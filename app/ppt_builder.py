"""Client-ready, template-driven CRO + AOV presentation builder."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

WIDE, HIGH = Inches(13.333), Inches(7.5)
INK, PAPER, WHITE = RGBColor(28, 25, 29), RGBColor(250, 247, 242), RGBColor(255, 255, 255)
MUTED, CORAL, ROSE, SAGE, LINE = RGBColor(106, 96, 102), RGBColor(214, 105, 92), RGBColor(247, 226, 220), RGBColor(220, 233, 222), RGBColor(225, 217, 211)


def _shape(slide, x, y, w, h, color, rounded=False):
    item = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE, x, y, w, h)
    item.fill.solid(); item.fill.fore_color.rgb = color; item.line.fill.background()
    return item


def _text(slide, text, x, y, w, h, size=14, color=INK, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame; frame.clear(); frame.word_wrap = True; frame.vertical_anchor = MSO_ANCHOR.TOP
    para = frame.paragraphs[0]; para.text = text; para.alignment = align
    para.font.name = "Aptos"; para.font.size = Pt(size); para.font.bold = bold; para.font.color.rgb = color; para.space_after = Pt(0)
    return box


def _base(prs, label="MOBILE CRO + AOV AUDIT"):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _shape(slide, 0, 0, WIDE, HIGH, PAPER)
    _text(slide, label.upper(), Inches(.55), Inches(.32), Inches(4.8), Inches(.2), 8, CORAL, True)
    _text(slide, "CRO PITCH AGENT", Inches(10.7), Inches(.32), Inches(2.05), Inches(.2), 8, MUTED, True, PP_ALIGN.RIGHT)
    return slide


def _footer(slide, number):
    _text(slide, f"{number:02d}", Inches(.55), Inches(7.05), Inches(.3), Inches(.18), 8, MUTED, True)
    _shape(slide, Inches(.98), Inches(7.13), Inches(11.8), Inches(.01), LINE)


def _title(slide, eyebrow, title, subtitle=""):
    _text(slide, eyebrow.upper(), Inches(.55), Inches(.7), Inches(5.6), Inches(.25), 9, CORAL, True)
    _text(slide, title, Inches(.55), Inches(1.02), Inches(8.3), Inches(.82), 28, INK, True)
    if subtitle: _text(slide, subtitle, Inches(.58), Inches(1.92), Inches(8.0), Inches(.55), 12, MUTED)


def _pill(slide, value, x, y, color=ROSE):
    _shape(slide, x, y, Inches(1.0), Inches(.3), color, True)
    _text(slide, value, x, y + Inches(.06), Inches(1.0), Inches(.16), 8, INK, True, PP_ALIGN.CENTER)


def _card(slide, heading, lines: Iterable[str], x, y, w, h, accent=CORAL):
    _shape(slide, x, y, w, h, WHITE, True)
    _shape(slide, x + Inches(.22), y + Inches(.24), Inches(.08), Inches(.08), accent, True)
    _text(slide, heading, x + Inches(.4), y + Inches(.18), w - Inches(.62), Inches(.3), 13, INK, True)
    body = "\n".join(f"• {line}" for line in lines if line) or "• Review during implementation"
    _text(slide, body, x + Inches(.28), y + Inches(.65), w - Inches(.56), h - Inches(.84), 11, MUTED)


def _mobile(slide, image_path, x, y, h):
    if image_path and Path(image_path).is_file(): slide.shapes.add_picture(image_path, x, y, height=h)
    else:
        _shape(slide, x, y, Inches(2.6), h, ROSE, True)
        _text(slide, "MOBILE\nSCREEN", x + Inches(.3), y + h / 2 - Inches(.25), Inches(2), Inches(.5), 13, MUTED, True, PP_ALIGN.CENTER)


def _priority_color(priority):
    return CORAL if priority == "P0" else RGBColor(215, 166, 83) if priority == "P1" else SAGE


def _page_slide(prs, page, number):
    slide = _base(prs, "CURRENT → PROPOSED")
    _title(slide, f"{page.get('priority', 'P2')} OPPORTUNITY", page.get("page_name", "Mobile screen"), page.get("summary", ""))
    _pill(slide, page.get("priority", "P2"), Inches(11.55), Inches(.78), _priority_color(page.get("priority", "P2")))
    _card(slide, "What is holding conversion back", page.get("issues", [])[:3], Inches(.55), Inches(2.8), Inches(3.65), Inches(3.65))
    _text(slide, "CURRENT EXPERIENCE", Inches(4.65), Inches(2.65), Inches(2), Inches(.2), 8, MUTED, True)
    _mobile(slide, page.get("screenshot_path"), Inches(4.65), Inches(2.95), Inches(3.7))
    _text(slide, "PROPOSED EXPERIENCE", Inches(8.85), Inches(2.65), Inches(2.4), Inches(.2), 8, CORAL, True)
    _mobile(slide, page.get("proposed_screenshot_path"), Inches(8.85), Inches(2.95), Inches(3.7))
    _footer(slide, number)


def _cover(prs, data):
    slide = prs.slides.add_slide(prs.slide_layouts[6]); _shape(slide, 0, 0, WIDE, HIGH, INK)
    _shape(slide, Inches(8.8), Inches(-1.4), Inches(5.5), Inches(5.5), CORAL)
    _shape(slide, Inches(10.5), Inches(4.7), Inches(3.1), Inches(3.1), RGBColor(70, 62, 68))
    _text(slide, "MOBILE CRO + AOV", Inches(.65), Inches(.72), Inches(4), Inches(.3), 10, RGBColor(246, 188, 177), True)
    _text(slide, data.get("brand_name", "Brand"), Inches(.6), Inches(1.32), Inches(7.4), Inches(1.05), 42, WHITE, True)
    _text(slide, "Conversion opportunity audit", Inches(.65), Inches(2.55), Inches(5), Inches(.35), 18, WHITE)
    _text(slide, data.get("website_url", ""), Inches(.65), Inches(6.52), Inches(5), Inches(.25), 10, RGBColor(205, 196, 198))


def build_pptx_from_audit(data: dict, output_path: str):
    prs = Presentation(); prs.slide_width, prs.slide_height = WIDE, HIGH
    pages, recommendations, aov = data.get("pages", []), data.get("recommendations", []), data.get("aov_opportunities", [])
    _cover(prs, data)
    slide = _base(prs, "EXECUTIVE SUMMARY")
    _title(slide, "THE OPPORTUNITY", "Turn mobile browsing into confident purchase decisions", data.get("executive_summary", ""))
    colors = [CORAL, RGBColor(215, 166, 83), RGBColor(102, 150, 115)]
    for i, rec in enumerate(recommendations[:3]): _card(slide, f"{rec.get('priority', 'P2')}  {rec.get('title', '')}", [rec.get("detail", "")], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.45), colors[i])
    _footer(slide, 2)
    slide = _base(prs, "AUDIT SCOPE")
    _title(slide, "AUDIT SCOPE", "A mobile-first review of the buying journey", "Every recommendation reduces decision friction or creates a relevant AOV lever.")
    for i, stage in enumerate(["Discover", "Browse", "Decide", "Add to cart", "Checkout"]):
        x = Inches(.65 + i * 2.48); _shape(slide, x, Inches(3.25), Inches(2.0), Inches(1.15), WHITE, True)
        _text(slide, f"0{i + 1}", x + Inches(.18), Inches(3.5), Inches(.35), Inches(.2), 9, CORAL, True); _text(slide, stage, x + Inches(.18), Inches(3.8), Inches(1.55), Inches(.25), 14, INK, True)
        if i < 4: _text(slide, "→", x + Inches(2.08), Inches(3.65), Inches(.3), Inches(.25), 16, CORAL, True)
    _footer(slide, 3)
    slide = _base(prs, "PRIORITY MAP")
    _title(slide, "PRIORITY MAP", "Focus investment where mobile confidence breaks down", "P0 = immediate, P1 = next sprint, P2 = validate and optimise.")
    for i, rec in enumerate(recommendations[:5]):
        y = Inches(2.7 + i * .65); _pill(slide, rec.get("priority", "P2"), Inches(.65), y, _priority_color(rec.get("priority", "P2")))
        _text(slide, rec.get("title", ""), Inches(1.9), y + Inches(.05), Inches(4.6), Inches(.25), 13, INK, True); _text(slide, rec.get("detail", ""), Inches(6.65), y + Inches(.05), Inches(5.8), Inches(.3), 10, MUTED)
    _footer(slide, 4)
    slide = _base(prs, "MOBILE CONVERSION LENS")
    _title(slide, "WHAT A HIGH-CONVERTING MOBILE FLOW NEEDS", "Make the decision easy before asking for commitment", "The audit evaluates these four recurring conversion mechanics across the buying journey.")
    mechanics = [("Clarity", "The product, price and proposition are easy to understand."), ("Confidence", "Trust, delivery and returns reduce hesitation."), ("Momentum", "The next action is visible at the right moment."), ("Relevance", "Merchandising helps shoppers discover the right add-on.")]
    for i, item in enumerate(mechanics):
        x, y = Inches(.6 + (i % 2) * 6.15), Inches(2.85 + (i // 2) * 1.45)
        _card(slide, item[0], [item[1]], x, y, Inches(5.65), Inches(1.05), colors[i % 3])
    _footer(slide, 5)
    number = 6
    for page in pages: _page_slide(prs, page, number); number += 1
    slide = _base(prs, "AOV OPPORTUNITIES")
    _title(slide, "GROW BASKET VALUE", "Use relevance—not interruption—to increase AOV", "Potential AOV levers: validate impact with storefront and analytics data.")
    for i, item in enumerate(aov[:3]): _card(slide, item.get("title", "AOV opportunity"), [f"Placement: {item.get('placement', '')}", item.get("description", ""), f"Potential: {item.get('expected_impact', 'medium')}"], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.6), colors[i])
    _footer(slide, number); number += 1
    slide = _base(prs, "AOV PLAYBOOK")
    _title(slide, "AOV PLAYBOOK", "Introduce the right add-on at the right decision moment", "The objective is to increase basket depth without introducing checkout friction.")
    steps = [("PDP", "Show compatible or matching items after product confidence is established."), ("CART", "Offer one clear, low-effort complementary addition before checkout."), ("COLLECTION", "Use edits and sets to help shoppers self-select into higher-value looks.")]
    for i, item in enumerate(steps): _card(slide, item[0], [item[1]], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.25), colors[i])
    _footer(slide, number); number += 1
    slide = _base(prs, "BENCHMARK LENS")
    _title(slide, "BENCHMARK LENS", "Borrow the pattern. Preserve the brand.", "Adapt category-leading patterns to solve a real problem—never copy another storefront.")
    patterns = [("Decision confidence", "Group price, delivery, returns and CTA."), ("Guided discovery", "Make filters, edits and paths easy to scan."), ("Relevant cross-sell", "Surface complementary items at the decision moment.")]
    for i, item in enumerate(patterns): _card(slide, item[0], [item[1], "Adapt to the existing visual system."], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.35), colors[i])
    _footer(slide, number); number += 1
    slide = _base(prs, "DESIGN PRINCIPLES")
    _title(slide, "PROPOSED EXPERIENCE", "A lighter, clearer mobile decision path", "Protect brand equity while making the next best action unmistakable.")
    for i, principle in enumerate(["One clear primary action", "Trust close to commitment", "Product context before persuasion", "AOV suggestions with a reason"]):
        x, y = Inches(.65 + (i % 2) * 6.1), Inches(3.0 + (i // 2) * 1.35); _shape(slide, x, y, Inches(5.55), Inches(.9), WHITE, True)
        _text(slide, f"0{i + 1}", x + Inches(.3), y + Inches(.3), Inches(.4), Inches(.2), 10, CORAL, True); _text(slide, principle, x + Inches(.9), y + Inches(.27), Inches(4.3), Inches(.26), 15, INK, True)
    _footer(slide, number); number += 1
    slide = _base(prs, "MEASUREMENT PLAN")
    _title(slide, "MEASURE WHAT CHANGES", "Use behaviour signals to validate the uplift", "Avoid unsupported revenue claims. Track directional movement against a baseline.")
    metrics = [("Conversion confidence", "PDP add-to-cart rate, CTA engagement, return-policy interaction"), ("Discovery quality", "Collection-to-PDP click-through, filter use, search refinement"), ("Basket depth", "Items per order, attachment rate, bundle/add-on acceptance")]
    for i, item in enumerate(metrics): _card(slide, item[0], [item[1]], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.25), colors[i])
    _footer(slide, number); number += 1
    slide = _base(prs, "IMPLEMENTATION ROADMAP")
    _title(slide, "IMPLEMENTATION ROADMAP", "Ship learning loops—not a one-time redesign", "Sequence changes by effort, confidence, and proximity to purchase intent.")
    phases = [("Quick confidence wins", "0–2 weeks · CTA hierarchy, trust cues, page clarity"), ("Merchandising upgrades", "2–6 weeks · cross-sell modules, discovery, bundles"), ("Measure and refine", "Ongoing · test, monitor, iterate on evidence")]
    for i, item in enumerate(phases): _card(slide, item[0], [item[1]], Inches(.55 + i * 4.18), Inches(3.0), Inches(3.85), Inches(2.35), colors[i])
    _footer(slide, number); number += 1
    slide = _base(prs, "DECISION SUMMARY")
    _title(slide, "THE RECOMMENDED DIRECTION", "Clarity first. Confidence second. Basket growth third.", "A focused sequence protects conversion while creating room for sustainable AOV growth.")
    summary = ["Make the first purchase decision easier on PDP and cart.", "Move evidence and reassurance nearer to the primary action.", "Add contextual product pairings only after the primary decision is clear."]
    _card(slide, "What to prioritise", summary, Inches(.55), Inches(3.0), Inches(7.2), Inches(2.35))
    _shape(slide, Inches(8.15), Inches(3.0), Inches(4.55), Inches(2.35), ROSE, True); _text(slide, "P0 → P1 →\nmeasure → iterate", Inches(8.65), Inches(3.65), Inches(3.4), Inches(.65), 20, INK, True)
    _footer(slide, number); number += 1
    slide = _base(prs, "NEXT STEPS")
    _title(slide, "THE FIRST SPRINT", "Start with the highest-confidence purchase blockers", "Use this deck as a prioritised brief for design, development, and experimentation.")
    _card(slide, "Recommended next actions", ["Validate proposed screens with brand and merchandising owners.", "Implement P0 conversion confidence improvements.", "Define product pairings and bundle rules for AOV experiments.", "Measure impact before expanding the programme."], Inches(.55), Inches(3.0), Inches(7.2), Inches(2.65))
    _shape(slide, Inches(8.15), Inches(3.0), Inches(4.55), Inches(2.65), INK, True); _text(slide, "Build a more confident\nmobile buying journey.", Inches(8.55), Inches(3.65), Inches(3.7), Inches(.8), 20, WHITE, True)
    _footer(slide, number)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); prs.save(output_path)
