from src.processor.cleaner import prune_dom
from src.processor.markdown import convert_html_to_clean_markdown
from src.processor.heuristics import extract_heuristics
from src.crawler.link_finder import discover_priority_subpages, normalize_url


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Acme Inc - Modern API Platform</title>
    <style>.hero { color: red; }</style>
    <script>console.log("tracking pixel");</script>
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about-us">About Us</a>
            <a href="/team">Leadership & Team</a>
            <a href="/pricing">Pricing Plans</a>
            <a href="/contact">Contact Sales</a>
            <a href="https://twitter.com/acme">Twitter</a>
        </nav>
    </header>

    <div class="cookie-banner modal">
        <p>Accept our cookies or leave.</p>
    </div>

    <main>
        <h1>Next-Gen Cloud Infrastructure</h1>
        <p>Acme helps developers build scalable microservices in minutes.</p>
        
        <h2>Who is it for?</h2>
        <p>Software engineers, DevOps architects, and enterprise backend teams.</p>

        <section id="leadership">
            <h3>Leadership Team</h3>
            <ul>
                <li>Alice Smith - CEO & Co-founder (<a href="https://www.linkedin.com/in/alicesmith">LinkedIn</a>)</li>
                <li>Bob Jones - CTO (<a href="https://www.linkedin.com/in/bobjones">LinkedIn</a>)</li>
            </ul>
        </section>

        <footer>
            <p>For inquiries, email us at <a href="mailto:contact@acme.com">contact@acme.com</a> or sales@acme.com</p>
            <svg height="100" width="100"><circle cx="50" cy="50" r="40" /></svg>
        </footer>
    </main>
</body>
</html>
"""


def test_dom_pruner():
    pruned = prune_dom(SAMPLE_HTML)
    assert "<script" not in pruned
    assert "<style" not in pruned
    assert "<svg" not in pruned
    assert "tracking pixel" not in pruned
    assert "cookie-banner" not in pruned
    assert "Next-Gen Cloud Infrastructure" in pruned


def test_markdown_conversion():
    pruned = prune_dom(SAMPLE_HTML)
    md = convert_html_to_clean_markdown(pruned, max_chars=5000)
    assert "# Next-Gen Cloud Infrastructure" in md or "Next-Gen Cloud Infrastructure" in md
    assert "Software engineers" in md
    assert "<script>" not in md
    assert "<html" not in md


def test_heuristics_extraction():
    heuristics = extract_heuristics(SAMPLE_HTML, domain="acme.com")
    assert "contact@acme.com" in heuristics.emails
    assert "sales@acme.com" in heuristics.emails
    assert "https://www.linkedin.com/in/alicesmith" in heuristics.linkedin_profiles
    assert "https://www.linkedin.com/in/bobjones" in heuristics.linkedin_profiles


def test_link_discovery():
    links = discover_priority_subpages(SAMPLE_HTML, base_url="https://acme.com", max_pages=4)
    assert len(links) > 0
    assert any("about" in url or "team" in url or "pricing" in url or "contact" in url for url in links)
    assert not any("twitter.com" in url for url in links)


def test_url_normalization():
    assert normalize_url("https://acme.com", "/about/") == "https://acme.com/about"
    assert normalize_url("https://acme.com", "pricing#details") == "https://acme.com/pricing"
