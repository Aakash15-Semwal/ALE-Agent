import asyncio
from typing import List
from src.config import settings
from src.utils.logger import logger
from src.crawler.browser import browser_manager
from src.crawler.page_fetcher import fetch_page, FetchedPage
from src.crawler.link_finder import discover_priority_subpages
from src.processor.cleaner import prune_dom
from src.processor.markdown import convert_html_to_clean_markdown
from src.processor.heuristics import extract_heuristics
from src.extractor.prompts import build_extraction_prompt
from src.extractor.llm_client import llm_client
from src.extractor.schema_enforcer import parse_and_validate_extraction, create_empty_fallback
from src.bonus.search_fallback import enrich_leadership_with_search
from src.bonus.cost_tracker import cost_tracker
from src.models import CompanyIntelligence, ExtractionMetadata
from src.utils.exporter import export_to_json, export_to_csv


class PipelineOrchestrator:
    """Coordinates page crawling, context preprocessing, LLM extraction, and enrichment."""

    async def enrich_domain(self, domain: str) -> CompanyIntelligence:
        logger.info(f"==> Starting enrichment for domain: [bold cyan]{domain}[/bold cyan]")
        domain_clean = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip("/")
        root_url = f"https://{domain_clean}"

        context = await browser_manager.create_stealth_context()
        crawled_urls: List[str] = []

        try:
            logger.info(f"[{domain_clean}] Crawling homepage: {root_url}")
            homepage = await fetch_page(context, root_url)

            if not homepage.success and not homepage.html:
                logger.warning(f"[{domain_clean}] Homepage unreachable ({homepage.error_message}). Generating fallback.")
                return create_empty_fallback(domain_clean, homepage.error_message or "Homepage unreachable")

            crawled_urls.append(homepage.final_url)
            pages_to_process: List[FetchedPage] = [homepage]

            # Discover relevant subpages from homepage navigation
            subpage_urls = discover_priority_subpages(
                html_content=homepage.html,
                base_url=homepage.final_url,
                max_pages=settings.max_subpages_per_domain
            )

            if subpage_urls:
                logger.info(f"[{domain_clean}] Concurrently crawling {len(subpage_urls)} subpages: {subpage_urls}")
                fetch_tasks = [fetch_page(context, sub_url) for sub_url in subpage_urls]
                subpage_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

                for res in subpage_results:
                    if isinstance(res, FetchedPage) and res.success and res.html:
                        pages_to_process.append(res)
                        crawled_urls.append(res.final_url)

            all_emails = set()
            all_linkedin_profiles = set()
            markdown_sections: List[str] = []

            for page in pages_to_process:
                heuristics = extract_heuristics(page.html, domain=domain_clean)
                all_emails.update(heuristics.emails)
                all_linkedin_profiles.update(heuristics.linkedin_profiles)

                pruned_html = prune_dom(page.html)
                page_md = convert_html_to_clean_markdown(pruned_html, max_chars=8000)
                if page_md:
                    markdown_sections.append(f"## Content from Page: {page.final_url}\n\n{page_md}")

            combined_markdown = "\n\n---\n\n".join(markdown_sections)
            logger.info(
                f"[{domain_clean}] Pre-processing finished. Crawled {len(pages_to_process)} pages. "
                f"Found {len(all_emails)} emails, {len(all_linkedin_profiles)} LinkedIn links."
            )

            user_prompt = build_extraction_prompt(
                domain=domain_clean,
                context_markdown=combined_markdown,
                heuristic_emails=sorted(list(all_emails)),
                heuristic_linkedin=sorted(list(all_linkedin_profiles))
            )

            logger.info(f"[{domain_clean}] Invoking LLM extraction ({settings.default_llm_provider})...")
            llm_response = llm_client.complete(user_prompt)

            estimated_cost = cost_tracker.record_usage(
                domain=domain_clean,
                model_name=llm_response.model_name,
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens
            )

            metadata = ExtractionMetadata(
                pages_crawled=crawled_urls,
                llm_provider=llm_response.provider,
                model_name=llm_response.model_name,
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
                estimated_cost_usd=estimated_cost,
                search_fallback_triggered=False
            )

            intelligence = parse_and_validate_extraction(
                raw_json_str=llm_response.raw_json,
                target_domain=domain_clean,
                metadata=metadata
            )

            # Query external search if founders or direct LinkedIn profiles are missing
            if settings.enable_search_fallback:
                needs_enrichment = (
                    not intelligence.key_leadership or
                    any(not m.linkedin_url for m in intelligence.key_leadership)
                )
                if needs_enrichment:
                    logger.info(f"[{domain_clean}] Triggering external search fallback for leadership LinkedIn URLs...")
                    enriched_leadership = enrich_leadership_with_search(
                        company_name=intelligence.company_name,
                        leadership=intelligence.key_leadership
                    )
                    intelligence.key_leadership = enriched_leadership
                    if intelligence.metadata:
                        intelligence.metadata.search_fallback_triggered = True

            logger.info(
                f"[{domain_clean}] Extraction successful. Confidence: {intelligence.data_confidence_score:.2f} "
                f"| Tokens: {llm_response.total_tokens} | Cost: ${estimated_cost:.6f}"
            )
            return intelligence

        except Exception as e:
            logger.error(f"[{domain_clean}] Uncaught exception during pipeline execution: {e}", exc_info=True)
            return create_empty_fallback(domain_clean, str(e))

        finally:
            await context.close()

    async def run_batch(self, domains: List[str]) -> List[CompanyIntelligence]:
        results: List[CompanyIntelligence] = []
        logger.info(f"Starting batch enrichment for {len(domains)} target domains: {domains}")

        try:
            await browser_manager.start()

            for idx, domain in enumerate(domains, start=1):
                logger.info(f"\nProcessing target [{idx}/{len(domains)}]: {domain}")
                try:
                    record = await self.enrich_domain(domain)
                    results.append(record)
                except Exception as domain_error:
                    logger.critical(f"Domain level failure on {domain}: {domain_error}")
                    results.append(create_empty_fallback(domain, str(domain_error)))

        finally:
            await browser_manager.close()

        export_to_json(results, settings.output_json_path)
        export_to_csv(results, settings.output_csv_path)

        return results


orchestrator = PipelineOrchestrator()
