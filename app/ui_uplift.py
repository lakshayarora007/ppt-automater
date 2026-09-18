"""Image-to-image mobile UI concepts based on a completed CRO audit."""
from __future__ import annotations

import base64
import json
import os
import shutil
from pathlib import Path
from typing import Any


def build_uplift_prompt(audit: dict[str, Any], page: dict[str, Any]) -> str:
    recommendations = [item["title"] for item in audit.get("recommendations", [])[:3]]
    issues = page.get("issues", [])[:3]
    return "\n".join(
        [
            "Use case: ui-mockup",
            "Asset type: client-ready mobile ecommerce CRO proposal slide.",
            "Input image: the supplied screenshot is the existing mobile storefront screen and is the edit target.",
            f"Primary request: redesign only this {page.get('page_name', 'mobile')} screen to address these observed conversion issues: {'; '.join(issues)}.",
            f"Recommended direction: {'; '.join(recommendations)}. You may adapt proven competitor interaction patterns only when they solve one of these issues; do not copy competitor branding or layout.",
            "Style: polished, realistic mobile ecommerce UI; 390x844 portrait composition.",
            "Constraints: preserve the existing logo, product photography, product identity, category, brand colour palette, and overall typography personality. Make only focused, minimal changes that directly address the listed issues. Do not over-design the screen.",
            "Do not invent products, prices, discounts, reviews, delivery promises, customer counts, or claims. Do not add watermarks. Keep all text short, readable, and non-overlapping.",
            "Deliver a single complete mobile screen, not a device mockup or before/after collage.",
        ]
    )


def _edit_image(source: Path, prompt: str, output: Path, model: str) -> None:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: pip install -r requirements.txt") from exc
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to .env before generating proposed screens.")

    client = OpenAI()
    with source.open("rb") as image:
        response = client.images.edit(
            model=model,
            image=image,
            prompt=prompt,
            size="1024x1536",
            quality="medium",
            output_format="png",
        )
    encoded = response.data[0].b64_json
    if not encoded:
        raise RuntimeError("Image API returned no image data.")
    output.write_bytes(base64.b64decode(encoded))


def uplift_audit(audit: dict[str, Any], output_dir: str | Path, max_screens: int = 3) -> dict[str, Any]:
    """Generate proposed screens and attach their non-destructive paths to audit JSON."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
    selected = [page for page in audit.get("pages", []) if page.get("screenshot_path")]
    selected.sort(key=lambda page: (page.get("priority") != "P0", page.get("priority") != "P1"))

    generated = 0
    for index, page in enumerate(selected):
        if generated >= max_screens:
            break
        source = Path(page["screenshot_path"])
        if not source.is_file():
            continue
        destination = target / f"{index + 1:02d}-{page.get('page_name', 'screen').lower().replace(' ', '-')}-proposed.png"
        _edit_image(source, build_uplift_prompt(audit, page), destination, model)
        page["proposed_screenshot_path"] = str(destination)
        generated += 1
    if not generated:
        raise RuntimeError("No real Playwright screenshots found in this audit. Run `audit` or `demo` first.")
    return audit


def load_and_uplift(audit_path: str | Path, output_dir: str | Path, max_screens: int) -> None:
    source = Path(audit_path)
    audit = json.loads(source.read_text(encoding="utf-8"))
    updated = uplift_audit(audit, output_dir, max_screens)
    source.write_text(json.dumps(updated, indent=2), encoding="utf-8")


def _priority_pages(audit: dict[str, Any], max_screens: int) -> list[dict[str, Any]]:
    pages = [page for page in audit.get("pages", []) if page.get("screenshot_path")]
    pages.sort(key=lambda page: (page.get("priority") != "P0", page.get("priority") != "P1"))
    return pages[:max_screens]


def prepare_chatgpt_handoff(audit_path: str | Path, jobs_dir: str | Path, max_screens: int) -> int:
    """Create upload-ready jobs for a user-controlled ChatGPT image-edit session.

    The user signs in themselves. Each job contains only the relevant screenshot,
    a focused prompt, and a manifest that lets us attach the downloaded result.
    """
    audit_source = Path(audit_path)
    audit = json.loads(audit_source.read_text(encoding="utf-8"))
    root = Path(jobs_dir)
    root.mkdir(parents=True, exist_ok=True)
    jobs: list[dict[str, str]] = []
    for number, page in enumerate(_priority_pages(audit, max_screens), start=1):
        screenshot = Path(page["screenshot_path"])
        if not screenshot.is_file():
            continue
        job = root / f"{number:02d}-{page.get('page_name', 'screen').lower().replace(' ', '-') }"
        job.mkdir(parents=True, exist_ok=True)
        upload = job / "current-screen.png"
        shutil.copy2(screenshot, upload)
        (job / "prompt.txt").write_text(build_uplift_prompt(audit, page), encoding="utf-8")
        jobs.append({"job_dir": str(job), "page_url": page.get("url", ""), "download_name": "proposed.png"})
    (root / "manifest.json").write_text(json.dumps({"audit_path": str(audit_source), "jobs": jobs}, indent=2), encoding="utf-8")
    return len(jobs)


def collect_chatgpt_results(jobs_dir: str | Path) -> int:
    """Attach user-downloaded `proposed.png` files to the original audit JSON."""
    root = Path(jobs_dir)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    audit_path = Path(manifest["audit_path"])
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    by_url = {page.get("url"): page for page in audit.get("pages", [])}
    attached = 0
    for job in manifest.get("jobs", []):
        candidate = Path(job["job_dir"]) / job.get("download_name", "proposed.png")
        page = by_url.get(job.get("page_url"))
        if candidate.is_file() and page:
            page["proposed_screenshot_path"] = str(candidate)
            attached += 1
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return attached
