import pytest

from app.ui_uplift import build_uplift_prompt, build_text_to_image_prompt, uplift_audit


def test_uplift_prompt_locks_brand_invariants():
    prompt = build_uplift_prompt(
        {"recommendations": [{"title": "Add a sticky CTA"}]},
        {"page_name": "Product Detail Page", "issues": ["CTA not visible"], "screenshot_path": "screen.png"},
    )
    assert "preserve the existing logo" in prompt
    assert "Do not invent products" in prompt
    assert "CTA not visible" in prompt
    assert "Do not over-design" in prompt


def test_uplift_auto_uses_local_when_openai_key_is_missing(monkeypatch, tmp_path):
    captured = {}

    def fake_render(source, page, output):
        captured["provider"] = "local"
        output.write_bytes(b"png")

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.ui_uplift._render_local_concept", fake_render)
    audit = {"recommendations": [], "pages": [{"page_name": "Home", "screenshot_path": str(tmp_path / "home.png"), "priority": "P0"}]}
    (tmp_path / "home.png").write_bytes(b"source")

    uplift_audit(audit, tmp_path / "out", max_screens=1)

    assert captured == {"provider": "local"}
    assert audit["pages"][0]["proposed_image_provider"] == "local"


def test_uplift_local_provider_renders_concept(monkeypatch, tmp_path):
    captured = {}

    def fake_render(source, page, output):
        captured["provider"] = "local"
        output.write_bytes(b"png")

    monkeypatch.setattr("app.ui_uplift._render_local_concept", fake_render)
    audit = {"pages": [{"page_name": "Home", "screenshot_path": str(tmp_path / "home.png"), "issues": ["CTA is unclear"], "priority": "P0"}]}
    (tmp_path / "home.png").write_bytes(b"source")

    uplift_audit(audit, tmp_path / "out", max_screens=1, provider="local")

    assert captured["provider"] == "local"


def test_uplift_openai_provider_uses_current_default_model(monkeypatch, tmp_path):
    captured = {}

    def fake_edit(source, prompt, output, model, provider):
        captured.update(model=model, provider=provider)
        output.write_bytes(b"png")

    monkeypatch.setattr("app.ui_uplift._edit_image", fake_edit)
    audit = {"pages": [{"page_name": "Home", "screenshot_path": str(tmp_path / "home.png"), "priority": "P0"}]}
    (tmp_path / "home.png").write_bytes(b"source")

    uplift_audit(audit, tmp_path / "out", max_screens=1, provider="openai")

    assert captured == {"model": "gpt-image-1", "provider": "openai"}


def test_uplift_auto_uses_openai_when_key_exists(monkeypatch, tmp_path):
    captured = {}

    def fake_edit(source, prompt, output, model, provider):
        captured.update(model=model, provider=provider)
        output.write_bytes(b"png")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.ui_uplift._edit_image", fake_edit)
    audit = {"pages": [{"page_name": "Home", "screenshot_path": str(tmp_path / "home.png"), "priority": "P0"}]}
    (tmp_path / "home.png").write_bytes(b"source")

    uplift_audit(audit, tmp_path / "out", max_screens=1)

    assert captured == {"model": "gpt-image-1", "provider": "openai"}


def test_uplift_can_filter_to_homepage(monkeypatch, tmp_path):
    captured = []

    def fake_render(source, page, output):
        captured.append(page["page_name"])
        output.write_bytes(b"png")

    monkeypatch.setattr("app.ui_uplift._render_local_concept", fake_render)
    pages = [
        {"page_name": "Homepage", "screenshot_path": str(tmp_path / "home.png"), "priority": "P2"},
        {"page_name": "Cart", "screenshot_path": str(tmp_path / "cart.png"), "priority": "P1"},
    ]
    for name in ("home.png", "cart.png"):
        (tmp_path / name).write_bytes(b"source")

    uplift_audit({"pages": pages}, tmp_path / "out", max_screens=1, provider="local", page_filter="Homepage")

    assert captured == ["Homepage"]


def test_uplift_generates_all_pages_when_no_limit_is_given(monkeypatch, tmp_path):
    captured = []

    def fake_render(source, page, output):
        captured.append(page["page_name"])
        output.write_bytes(b"png")

    monkeypatch.setattr("app.ui_uplift._render_local_concept", fake_render)
    pages = [
        {"page_name": "Homepage", "screenshot_path": str(tmp_path / "home.png"), "priority": "P1"},
        {"page_name": "Product Detail Page", "screenshot_path": str(tmp_path / "product.png"), "priority": "P0"},
        {"page_name": "Cart", "screenshot_path": str(tmp_path / "cart.png"), "priority": "P1"},
    ]
    for name in ("home.png", "product.png", "cart.png"):
        (tmp_path / name).write_bytes(b"source")

    uplift_audit({"pages": pages}, tmp_path / "out", provider="local")

    assert captured == ["Product Detail Page", "Homepage", "Cart"]


def test_uplift_sanitizes_page_names_for_output_files(monkeypatch, tmp_path):
    def fake_render(source, page, output):
        output.write_bytes(b"png")

    monkeypatch.setattr("app.ui_uplift._render_local_concept", fake_render)
    source = tmp_path / "trust.png"
    source.write_bytes(b"source")

    uplift_audit(
        {"pages": [{"page_name": "Trust / Information Page", "screenshot_path": str(source)}]},
        tmp_path / "out",
        provider="local",
    )

    assert (tmp_path / "out" / "01-trust-information-page-proposed.png").is_file()


def test_nvidia_uses_native_image_endpoint(monkeypatch, tmp_path):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            from PIL import Image
            from io import BytesIO
            import base64

            image = Image.new("RGB", (2, 2), (255, 0, 0))
            buffer = BytesIO()
            image.save(buffer, format="JPEG")
            return {"artifacts": [{"base64": base64.b64encode(buffer.getvalue()).decode("ascii"), "finishReason": "SUCCESS"}]}

    captured = {}

    def fake_post(endpoint, headers, json, timeout):
        captured.update(endpoint=endpoint, payload=json)
        return FakeResponse()

    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr("app.ui_uplift.requests.post", fake_post)
    source = tmp_path / "screen.png"
    output = tmp_path / "proposed.png"
    source.write_bytes(b"source")

    from app.ui_uplift import _edit_image

    _edit_image(source, "Create a polished mobile screen", output, "black-forest-labs/flux.1-dev", "nvidia")

    assert captured["endpoint"].endswith("/v1/genai/black-forest-labs/flux.1-dev")
    assert captured["payload"]["mode"] == "base"
    assert captured["payload"]["height"] == 1344
    assert captured["payload"]["cfg_scale"] == 0
    assert captured["payload"]["steps"] == 4
    assert output.read_bytes().startswith(b"\x89PNG")


def test_nvidia_prompt_blocks_phone_mockups():
    prompt = build_text_to_image_prompt(
        {"brand_name": "Attrangi", "recommendations": []},
        {"page_name": "Product Detail Page", "issues": ["CTA not visible"]},
    )

    assert "flat UI concept" in prompt
    assert "phone mockup" in prompt
    assert "iPhone frame" in prompt


def test_explicit_nvidia_failure_is_not_replaced_by_local_mockup(monkeypatch, tmp_path):

    def fake_edit(source, prompt, output, model, provider):
        output.write_bytes(b"bad-image")

    monkeypatch.setattr("app.ui_uplift._edit_image", fake_edit)
    monkeypatch.setattr("app.ui_uplift._looks_deck_ready", lambda output: False)
    audit = {"pages": [{"page_name": "Home", "screenshot_path": str(tmp_path / "home.png"), "priority": "P0"}]}
    (tmp_path / "home.png").write_bytes(b"source")

    with pytest.raises(RuntimeError, match="unusable proposed image"):
        uplift_audit(audit, tmp_path / "out", max_screens=1, provider="nvidia")
