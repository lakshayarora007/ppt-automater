from __future__ import annotations

from typing import List

from app.crawler import PageSnapshot
from app.models import AOVOpportunity, AuditReport, Issue, PageAudit, Recommendation


def _finding_for_snapshot(snapshot: PageSnapshot, text: str) -> Issue | None:
    evidence = f"{snapshot.name} page text at {snapshot.url}"
    if snapshot.page_type == "pdp" and "add to cart" not in text and "buy now" not in text:
        return Issue(
            title="Primary purchase action is not detectable in the product-page content",
            category="CRO",
            severity="Critical",
            primary_kpi="ATC",
            secondary_kpi="CVR",
            evidence=[evidence, "Neither 'Add to cart' nor 'Buy now' was found in the captured page text."],
            why_it_matters="Shoppers may not see a clear next step after evaluating the product, creating friction at the highest-intent stage.",
            recommendation="Keep one dominant Add to bag action visible in the first mobile viewport and repeat it in a sticky purchase bar after scroll.",
            expected_impact="Likely positive impact on add-to-cart rate and mobile CVR.",
        )
    if snapshot.page_type in {"pdp", "cart"} and "shipping" not in text and "delivery" not in text:
        return Issue(
            title="Delivery reassurance is absent from the purchase-stage content",
            category="CRO",
            severity="High",
            primary_kpi="CVR",
            secondary_kpi="Checkout Completion",
            evidence=[evidence, "No 'shipping' or 'delivery' language was found in the captured content."],
            why_it_matters="Unanswered fulfilment questions can delay commitment or push shoppers to leave before checkout.",
            recommendation="Place an explicit delivery estimate, shipping threshold, and returns link beside the CTA or order summary.",
            expected_impact="Likely reduction in purchase hesitation and checkout abandonment.",
        )
    if snapshot.page_type == "pdp" and "review" not in text and "rating" not in text:
        return Issue(
            title="Product-page decision support lacks observable review or rating content",
            category="Trust / Purchase Confidence",
            severity="High",
            primary_kpi="CVR",
            secondary_kpi="ATC",
            evidence=[evidence, "No 'review' or 'rating' language was found in the captured content."],
            why_it_matters="A shopper evaluating an unfamiliar product has less confidence at the point where purchase intent is highest.",
            recommendation="Add an honest review summary, rating count, and product-specific proof near the title or CTA; show an empty state clearly when no reviews exist.",
            expected_impact="Potential improvement in product confidence and add-to-cart rate.",
        )
    if snapshot.page_type == "collection" and "filter" not in text and "sort" not in text:
        return Issue(
            title="Collection content exposes no observable filtering or sorting path",
            category="Product Discovery",
            severity="High",
            primary_kpi="Engagement",
            secondary_kpi="CVR",
            evidence=[evidence, "No 'filter' or 'sort' language was found in the captured collection content."],
            why_it_matters="Shoppers with a specific style, category, or price intent must scan more of the catalogue before reaching a relevant product.",
            recommendation="Add persistent mobile filter and sort controls with category, price, availability, and style facets that remain easy to reopen.",
            expected_impact="Improved product discovery and collection-to-product click-through.",
        )
    if snapshot.page_type == "pdp" and not any(term in text for term in ("frequently bought", "complete the look", "bundle", "pair with")):
        return Issue(
            title="Product detail content has no observable complementary-product pathway",
            category="AOV Opportunity",
            severity="High",
            primary_kpi="AOV",
            secondary_kpi="Revenue",
            evidence=[evidence, "No 'frequently bought', 'complete the look', bundle, or pairing language was found."],
            why_it_matters="A shopper who is already evaluating a product is not given a contextual reason to add a relevant companion item.",
            recommendation="Add a compact complementary-products module below the primary decision zone with product-specific pairings and a low-friction add-to-bag action.",
            expected_impact="Potential increase in attachment rate, items per order, and AOV.",
        )
    if snapshot.page_type == "cart" and not any(term in text for term in ("recommended", "you may also like", "frequently bought", "add-on", "bundle")):
        return Issue(
            title="Cart content has no observable contextual add-on prompt",
            category="AOV Opportunity",
            severity="High",
            primary_kpi="AOV",
            secondary_kpi="Checkout Completion",
            evidence=[evidence, "No recommendation, add-on, frequently bought, or bundle language was found in the captured cart content."],
            why_it_matters="The cart is a high-intent moment to increase basket depth, but shoppers are not shown a relevant next product choice.",
            recommendation="Test one clearly explained complementary add-on or bundle suggestion above checkout, while keeping the primary checkout action dominant.",
            expected_impact="Potential AOV improvement without changing the primary checkout path.",
        )
    return None


def _recommendations_from_findings(findings: list[Issue]) -> list[Recommendation]:
    priority_by_severity = {"Critical": "P0", "High": "P1", "Medium": "P2", "Low": "P2"}
    return [
        Recommendation(
            title=finding.title,
            detail=f"{finding.recommendation} Primary KPI: {finding.primary_kpi}.",
            priority=priority_by_severity.get(finding.severity, "P2"),
        )
        for finding in findings[:5]
    ]


def analyze_pages(site_url: str, snapshots: List[PageSnapshot]) -> AuditReport:
    pages: List[PageAudit] = []
    findings: list[Issue] = []
    for snapshot in snapshots:
        text = (snapshot.text or "").lower()
        finding = _finding_for_snapshot(snapshot, text)
        if finding and not any(item.title == finding.title and item.evidence[0] == finding.evidence[0] for item in findings):
            findings.append(finding)
        issues = [finding.title] if finding else ["No high-confidence text-only issue detected; validate the rendered screenshot before changing layout."]

        pages.append(
            PageAudit(
                page_name=snapshot.name,
                url=snapshot.url,
                issues=issues[:3],
                priority="P1" if snapshot.page_type in {"pdp", "cart"} else "P2",
                summary=(
                    f"{snapshot.name} was assessed from its available mobile page text; visual hierarchy should be verified with a rendered screenshot."
                ),
                screenshot_path=snapshot.screenshot_path,
            )
        )

    aov = [
        AOVOpportunity(
            title="Complete the look",
            placement="PDP",
            description="Bundle complementary products near the purchase trigger to increase items per order.",
            expected_impact="high",
        ),
        AOVOpportunity(
            title="Bundle & Save",
            placement="Cart",
            description="Offer savings when customers add a second or third item before checkout.",
            expected_impact="high",
        ),
        AOVOpportunity(
            title="Frequently bought together",
            placement="PDP",
            description="Display paired products with a clear value hook and minimal extra attention demand.",
            expected_impact="medium",
        ),
    ]

    recommendations = _recommendations_from_findings(findings) or [
        Recommendation(
            title="Validate the rendered purchase journey",
            detail="Use the captured mobile screenshots to confirm the highest-impact friction before implementation. Primary KPI: CVR.",
            priority="P2",
        )
    ]

    return AuditReport(
        brand_name="CRO Audit",
        website_url=site_url,
        executive_summary=(
            "The highest-confidence opportunities are concentrated in the observed purchase and discovery paths: "
            + " ".join(f.title + "." for f in findings[:3])
            if findings
            else "No high-confidence text-only issue was confirmed; the next step is screenshot and analytics validation."
        ),
        pages=pages,
        aov_opportunities=aov,
        recommendations=recommendations,
        deck_outline=[
            "Executive summary",
            "Mobile funnel review",
            "Homepage and catalog findings",
            "Product page conversion friction",
            "Cart and checkout optimization",
            "AOV opportunities",
            "Competitor benchmark patterns",
            "Proposed mobile UX changes",
            "Implementation roadmap",
            "Final recommendation",
        ],
        findings=findings[:8],
    )
