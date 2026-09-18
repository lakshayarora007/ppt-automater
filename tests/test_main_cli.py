from pathlib import Path

import main


def test_generate_deck_can_run_image_uplift_before_ppt(monkeypatch, tmp_path):
    calls = []

    def fake_audit(url, brand, output):
        calls.append(("audit", url, brand, Path(output).name))

    def fake_uplift(input_path, output_dir, max_screens, provider, page_filter):
        calls.append(("uplift", Path(input_path).name, Path(output_dir).name, max_screens, provider, page_filter))

    def fake_ppt(input_path, output):
        calls.append(("ppt", Path(input_path).name, Path(output).name))

    monkeypatch.setattr(main, "_run_audit", fake_audit)
    monkeypatch.setattr(main, "_run_uplift", fake_uplift)
    monkeypatch.setattr(main, "_run_ppt", fake_ppt)

    main._run_generate_deck(
        url="https://example.com",
        brand="Example",
        output_dir=str(tmp_path / "example"),
        with_images=True,
        image_provider="auto",
        max_screens=2,
    )

    assert calls == [
        ("audit", "https://example.com", "Example", "audit.json"),
        ("uplift", "audit.json", "proposed-screens", 2, "auto", None),
        ("ppt", "audit.json", "cro-aov-deck.pptx"),
    ]
