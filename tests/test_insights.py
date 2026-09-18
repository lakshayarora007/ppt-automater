from app.crawler import PageSnapshot
from app.insights import analyze_pages


def test_analyze_pages_returns_specific_kpi_findings_and_no_generic_cue_fallback():
    report = analyze_pages(
        "https://example.com",
        [
            PageSnapshot(
                name="Product Detail Page",
                url="https://example.com/products/item",
                title="Item",
                text="A beautiful item with price and details",
                page_type="pdp",
            )
        ],
    )

    assert len(report.findings) == 1
    assert report.findings[0].primary_kpi == "ATC"
    assert "No purchase CTA was detected" not in report.pages[0].issues[0]
    assert report.recommendations[0].title == report.findings[0].title


def test_analyze_pages_surfaces_aov_gap_when_cross_sell_is_absent():
    report = analyze_pages(
        "https://example.com",
        [PageSnapshot("Cart", "https://example.com/cart", "Cart", "Your cart checkout delivery available", "cart")],
    )

    assert report.findings[0].primary_kpi == "AOV"
    assert "add-on" in report.findings[0].title.lower()