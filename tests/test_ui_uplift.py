from app.ui_uplift import build_uplift_prompt


def test_uplift_prompt_locks_brand_invariants():
    prompt = build_uplift_prompt(
        {"recommendations": [{"title": "Add a sticky CTA"}]},
        {"page_name": "Product Detail Page", "issues": ["CTA not visible"], "screenshot_path": "screen.png"},
    )
    assert "preserve the existing logo" in prompt
    assert "Do not invent products" in prompt
    assert "CTA not visible" in prompt
    assert "Do not over-design" in prompt

