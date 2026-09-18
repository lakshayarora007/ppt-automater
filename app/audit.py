from __future__ import annotations

from typing import List

from app.models import AOVOpportunity, AuditReport, PageAudit, Recommendation


def _heuristic_page_audits(url: str) -> List[PageAudit]:
    return [
        PageAudit(
            page_name="Homepage",
            url=f"{url}/",
            issues=[
                "Hero CTA is not immediately tied to a strong product value proposition.",
                "Mobile navigation may feel heavy if it lacks quick category paths.",
            ],
            priority="P1",
            summary="Homepage needs a clearer conversion hook and faster path to the product catalogue.",
        ),
        PageAudit(
            page_name="Collection Page",
            url=f"{url}/collections",
            issues=[
                "Product discovery may be slowed by overcrowded merchandising blocks.",
                "Users may not see a clear trust signal before they browse deeper.",
            ],
            priority="P1",
            summary="Collection pages need stronger filtering and decision-support content.",
        ),
        PageAudit(
            page_name="Product Page",
            url=f"{url}/products",
            issues=[
                "Purchase confidence may be diluted if price, shipping, and CTA are not close together.",
                "AOV opportunities may be underused if related products are placed too late.",
            ],
            priority="P0",
            summary="The product page is the most critical conversion point and should anchor bundles and trust cues.",
        ),
        PageAudit(
            page_name="Cart",
            url=f"{url}/cart",
            issues=[
                "Cart can improve by prompting bundle add-ons before checkout.",
                "Urgency or delivery reassurance is often not reinforced at the final step.",
            ],
            priority="P1",
            summary="Cart experience should reduce abandonment through bundle suggestions and reassurance.",
        ),
    ]


def _heuristic_aov() -> List[AOVOpportunity]:
    return [
        AOVOpportunity(
            title="Complete the Look",
            placement="Product Detail Page",
            description="Display matching accessories, add-ons, or product sets near the primary purchase decision to increase basket depth.",
            expected_impact="high",
        ),
        AOVOpportunity(
            title="Bundle & Save",
            placement="Cart",
            description="Offer a simple bundle jump point when the user is close to checkout to increase average order value without adding friction.",
            expected_impact="high",
        ),
        AOVOpportunity(
            title="Frequently Bought Together",
            placement="Product Detail Page",
            description="Create a small, visually clear collection of complementary items with price savings cues.",
            expected_impact="medium",
        ),
    ]


def _heuristic_recommendations() -> List[Recommendation]:
    return [
        Recommendation(
            title="Improve above-the-fold mobile hierarchy",
            detail="Place the offer, trust signal, and primary CTA in the first screen so purchase intent is visible before users scroll.",
            priority="P0",
        ),
        Recommendation(
            title="Introduce bundle merchandising earlier",
            detail="Add complementary products as a clear suggestion before checkout so the user can add one more item with low friction.",
            priority="P1",
        ),
        Recommendation(
            title="Reinforce trust near CTA",
            detail="Keep shipping, returns, and social proof close to the purchase trigger to reduce hesitation and checkout drop-off.",
            priority="P1",
        ),
    ]


def _deck_outline() -> List[str]:
    return [
        "Executive summary",
        "Current mobile funnel issues",
        "Homepage and category analysis",
        "Product page conversion friction",
        "Cart and checkout hesitation points",
        "AOV opportunity review",
        "Competitor benchmark patterns",
        "Recommended mobile UX direction",
        "Priority roadmap",
        "Final recommendation slide",
    ]


def run_audit(url: str, brand_name: str) -> AuditReport:
    pages = _heuristic_page_audits(url)
    aov_opps = _heuristic_aov()
    recommendations = _heuristic_recommendations()

    return AuditReport(
        brand_name=brand_name,
        website_url=url,
        executive_summary=(
            "The site has a viable brand and category fit, but the mobile funnel is likely losing conversion "
            "value where trust, clarity, and purchase momentum are fragmented. The biggest opportunity is to "
            "increase clarity at the product and cart stages while introducing bundle-led AOV lifts."
        ),
        pages=pages,
        aov_opportunities=aov_opps,
        recommendations=recommendations,
        deck_outline=_deck_outline(),
    )
