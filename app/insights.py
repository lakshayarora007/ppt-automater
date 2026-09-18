from __future__ import annotations

from typing import List

from app.crawler import PageSnapshot
from app.models import AOVOpportunity, AuditReport, PageAudit, Recommendation


def analyze_pages(site_url: str, snapshots: List[PageSnapshot]) -> AuditReport:
    pages: List[PageAudit] = []
    for snapshot in snapshots:
        text = (snapshot.text or "").lower()
        issues = []
        if snapshot.page_type == "pdp" and "add to cart" not in text and "buy now" not in text:
            issues.append("No purchase CTA was detected in the page text; verify that Add to Cart is clearly visible on mobile.")
        if snapshot.page_type in {"pdp", "cart"} and "shipping" not in text and "delivery" not in text:
            issues.append("No delivery or shipping reassurance was detected in the page text near the purchase stage.")
        if snapshot.page_type == "pdp" and "review" not in text and "rating" not in text:
            issues.append("No review or rating language was detected on this product page; add visible decision-support social proof where appropriate.")
        if snapshot.page_type == "collection" and "filter" not in text and "sort" not in text:
            issues.append("No filter or sort language was detected; verify product discovery controls are easy to use on mobile.")
        if not issues:
            issues.append("Key textual conversion cues are present. Validate their visual prominence in a browser screenshot before changing the layout.")

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

    recommendations = [
        Recommendation(
            title="Strengthen above-the-fold mobile hierarchy",
            detail="Keep the product promise, CTA, trust message, and price in one clear decision zone.",
            priority="P0",
        ),
        Recommendation(
            title="Increase bundle visibility",
            detail="Create a friction-light add-on experience before checkout to lift AOV without slowing the funnel.",
            priority="P1",
        ),
        Recommendation(
            title="Improve delivery and trust cues",
            detail="Place shipping, returns, and trust content closer to the CTA to reduce mobile hesitation.",
            priority="P1",
        ),
    ]

    return AuditReport(
        brand_name="CRO Audit",
        website_url=site_url,
        executive_summary=(
            "The site likely has conversion opportunities in the mobile decision path, especially around clear product value, trust reinforcement, and bundle-led AOV lifts."
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
    )
