"""CLI runner for the autonomous lead enrichment agent."""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.config import settings
from src.utils.logger import logger
from src.orchestrator import orchestrator
from src.bonus.cost_tracker import cost_tracker
from src.models import CompanyIntelligence

console = Console()

DEFAULT_DOMAINS = [
    "postman.com",
    "supabase.com",
    "vapi.ai"
]


def print_banner() -> None:
    banner_text = (
        "[bold cyan]Autonomous Lead Enrichment Agent[/bold cyan]\n"
        "[dim]Playwright Headless Crawling • Token-Optimized Markdown • Strict Pydantic Schema[/dim]\n"
        "[yellow]Target Assignment: SoftwareBrio AI Engineer Intern[/yellow]"
    )
    console.print(Panel.fit(banner_text, border_style="cyan"))


def display_results_table(records: List[CompanyIntelligence]) -> None:
    table = Table(title="Extracted Lead Intelligence Summary", show_header=True, header_style="bold cyan")
    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Company Name", style="bold white")
    table.add_column("Target Audience / ICP", style="dim white", max_width=40)
    table.add_column("Emails", justify="center", style="green")
    table.add_column("Leadership", justify="center", style="blue")
    table.add_column("Confidence", justify="right", style="bold yellow")

    for r in records:
        conf_style = "green" if r.data_confidence_score >= 0.7 else ("yellow" if r.data_confidence_score >= 0.4 else "red")
        table.add_row(
            r.domain,
            r.company_name,
            r.target_audience_icp,
            str(len(r.contact_points)),
            str(len(r.key_leadership)),
            f"[{conf_style}]{r.data_confidence_score:.2f}[/{conf_style}]"
        )

    console.print()
    console.print(table)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous Lead Enrichment Agent - Crawls domains and extracts structured intelligence using LLMs."
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        help="Space-separated list of target company domains (e.g., postman.com supabase.com vapi.ai)."
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Path to a text file containing domains, one per line."
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "groq"],
        help="Override active LLM provider (gemini, openai, groq)."
    )
    parser.add_argument(
        "--no-search",
        action="store_true",
        help="Disable external search fallback for missing founder LinkedIn profiles."
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Launch browser in visible UI mode (default is headless)."
    )
    return parser.parse_args()


async def main_async() -> int:
    print_banner()
    args = parse_arguments()

    if args.domains:
        target_domains = [d.strip() for d in args.domains if d.strip()]
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            console.print(f"[bold red]Error:[/bold red] Domain file not found: {file_path}")
            return 1
        with open(file_path, "r", encoding="utf-8") as f:
            target_domains = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        target_domains = DEFAULT_DOMAINS

    if args.provider:
        settings.default_llm_provider = args.provider
    if args.no_search:
        settings.enable_search_fallback = False
    if args.headful:
        settings.browser_headless = False

    # Fail fast if credentials for selected provider are missing
    try:
        settings.validate_active_provider_key()
    except ValueError as val_err:
        console.print(Panel(
            f"[bold red]API Configuration Notice:[/bold red]\n{str(val_err)}\n\n"
            f"[dim]Please update your .env file with your API key or pass --provider <provider>.[/dim]",
            border_style="red"
        ))
        return 1

    console.print(
        f"[bold]Active Provider:[/bold] [magenta]{settings.default_llm_provider}[/magenta] "
        f"(Model: [blue]{settings.get_active_model_name()}[/blue]) | "
        f"[bold]Search Fallback:[/bold] {'[green]Enabled[/green]' if settings.enable_search_fallback else '[red]Disabled[/red]'} | "
        f"[bold]Headless:[/bold] {settings.browser_headless}"
    )

    records = await orchestrator.run_batch(target_domains)
    display_results_table(records)

    if settings.enable_cost_tracking and cost_tracker.records:
        console.print()
        console.print(cost_tracker.create_summary_table())

    console.print()
    console.print(Panel(
        f"[bold green]Batch Enrichment Complete![/bold green]\n"
        f"• JSON Output: [cyan]{settings.output_json_path.resolve()}[/cyan]\n"
        f"• CSV Output:  [cyan]{settings.output_csv_path.resolve()}[/cyan]",
        border_style="green"
    ))

    return 0


def main() -> None:
    try:
        exit_code = asyncio.run(main_async())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Execution aborted by user.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
