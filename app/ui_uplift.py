"""Image-to-image mobile UI concepts based on a completed CRO audit."""
from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

MIN_SHARPNESS_SCORE = 8.0


def build_uplift_prompt(audit: dict[str, Any], page: dict[str, Any]) -> str:
    recommendations = [item["title"] for item in audit.get("recommendations", [])[:3]]
    issues = page.get("issues", [])[:3]
    return "\n".join(
        [
            "Use case: ui-mockup",
            "Asset type: client-ready mobile ecommerce CRO proposal slide.",
            f"Brand: {audit.get('brand_name', 'the existing brand')}.",
            "Input image: use the supplied screenshot as the visual reference for the existing storefront.",
            f"Primary request: redesign only this {page.get('page_name', 'mobile')} screen to address these observed conversion issues: {'; '.join(issues)}.",
            f"Recommended direction: {'; '.join(recommendations)}. You may adapt proven competitor interaction patterns only when they solve one of these issues; do not copy competitor branding or layout.",
            "Style: polished, realistic mobile ecommerce UI; 390x844 portrait composition.",
            "Composition: create a complete finished storefront screen with a strong visual hierarchy, generous spacing, premium jewellery ecommerce styling, refined cards, clear CTA placement, and a restrained editorial layout. It must look like a final design proposal, not a wireframe, diagnostic overlay, or presentation mockup.",
            "Output framing: flat 2D app screen only, edge-to-edge interface filling the whole canvas. No phone device, no iPhone frame, no hands, no browser chrome, no shadowed mockup, no perspective view, no blurred camera photo.",
            "Constraints: preserve the existing logo, product photography, product identity, category, brand colour palette, and overall typography personality. Make only focused, minimal changes that directly address the listed issues. Do not over-design the screen.",
            "Do not invent products, prices, discounts, reviews, delivery promises, customer counts, or claims. If source text is unreadable, use short neutral labels such as Add to bag, Details, Delivery, Returns, Filter, or View bag. Do not add watermarks. Keep all text short, readable, and non-overlapping.",
            "Deliver a single complete mobile screen, not a device mockup or before/after collage.",
        ]
    )


def build_text_to_image_prompt(audit: dict[str, Any], page: dict[str, Any]) -> str:
    """Prompt variant for providers that cannot edit the actual screenshot."""
    base = build_uplift_prompt(audit, page)
    return "\n".join(
        [
            base,
            "",
            "Provider note: this model cannot directly edit the uploaded screenshot, so create a new flat UI concept inspired by the brand and page type.",
            "The image must look like a clean ecommerce product screen capture exported from Figma: sharp, legible, aligned, and cropped exactly to the app viewport.",
            "Absolute negative prompt: blurry, low resolution, phone mockup, iPhone frame, camera photo, 3D render, hand holding phone, white device bezel, presentation slide, collage, watermark, gibberish text.",
        ]
    )


def _ollama_prompt(source: Path, prompt: str) -> str:
    """Use a local Ollama vision model to tighten the image-edit brief."""
    model = os.getenv("OLLAMA_MODEL", "llama3.2-vision")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    endpoint = base_url + "/api/chat"
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Review this mobile ecommerce screenshot and return only concise, concrete additions "
                    "to the following UI uplift brief. Preserve the existing brand and product identity.\n\n"
                    + prompt
                ),
                "images": [base64.b64encode(source.read_bytes()).decode("ascii")],
            }
        ],
    }
    headers = {}
    if api_key := os.getenv("OLLAMA_API_KEY"):
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        content = response.json().get("message", {}).get("content", "").strip()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Ollama is unavailable at {endpoint}. Start Ollama and pull {model}."
        ) from exc
    if not content:
        raise RuntimeError("Ollama returned an empty design brief.")
    return f"{prompt}\n\nLocal visual QA notes from Ollama:\n{content}"


def _openai_client(provider: str):
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: pip install -r requirements.txt") from exc

    if provider == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured. Add it to .env before using NVIDIA.")
        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to .env before using OpenAI.")
    return OpenAI()


def _edit_image(source: Path, prompt: str, output: Path, model: str, provider: str) -> None:
    if provider == "ollama":
        prompt = _ollama_prompt(source, prompt)
        provider = os.getenv("OLLAMA_IMAGE_PROVIDER", "nvidia").lower()
        if provider == "ollama":
            raise RuntimeError(
                "Ollama can analyse screenshots locally, but it cannot generate the final image. "
                "Set OLLAMA_IMAGE_PROVIDER=nvidia or use --provider nvidia."
            )

    if provider == "nvidia":
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured. Add it to .env before using NVIDIA.")
        mode = os.getenv("NVIDIA_IMAGE_MODE", "generate").lower()
        endpoint = os.getenv(
            "NVIDIA_IMAGE_URL",
            "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-dev",
        )
        if mode == "edit":
            raise RuntimeError(
                "NVIDIA hosted preview image editing accepts only example_id images, not local screenshots. "
                "Use NVIDIA_IMAGE_MODE=generate for proposed UI concepts or use --provider local."
            )
        payload = {
            "prompt": prompt,
            "mode": "base",
            "width": 768,
            "height": 1344,
            "cfg_scale": float(os.getenv("NVIDIA_CFG_SCALE", "0")),
            "seed": 0,
            "steps": int(os.getenv("NVIDIA_STEPS", "4")),
        }
        endpoints = [endpoint]
        fallback_endpoint = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.1-schnell"
        if endpoint != fallback_endpoint:
            endpoints.append(fallback_endpoint)
        last_failure = "unknown NVIDIA image failure"
        for attempt_endpoint in endpoints:
            try:
                response = requests.post(
                    attempt_endpoint,
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                    json=payload,
                    timeout=180,
                )
                response.raise_for_status()
                artifacts = response.json().get("artifacts", [])
                artifact = artifacts[0] if artifacts else {}
                encoded = artifact.get("base64")
                finish_reason = artifact.get("finishReason", "SUCCESS")
                if finish_reason != "SUCCESS":
                    last_failure = f"finishReason={finish_reason} from {attempt_endpoint}"
                    continue
                if not encoded:
                    last_failure = f"no base64 artifact from {attempt_endpoint}"
                    continue
                image_bytes = base64.b64decode(encoded)
                from PIL import Image
                from io import BytesIO

                generated = Image.open(BytesIO(image_bytes)).convert("RGB")
                extrema = generated.getextrema()
                if all(high <= 2 for low, high in extrema):
                    last_failure = f"blank artifact from {attempt_endpoint}"
                    continue
                generated.save(output, format="PNG")
                return
            except requests.HTTPError as exc:
                if response.status_code == 401:
                    raise RuntimeError(
                        "NVIDIA rejected the API key (401). Use a current NVIDIA NIM API key "
                        "from build.nvidia.com, not an Ollama Cloud key, and update NVIDIA_API_KEY in .env."
                    ) from exc
                last_failure = f"HTTP {response.status_code}: {response.text[:300]}"
            except requests.RequestException as exc:
                last_failure = str(exc)
            except Exception as exc:
                last_failure = f"invalid image artifact: {exc}"
        raise RuntimeError(f"NVIDIA image generation failed without a usable image: {last_failure}")

    client = _openai_client(provider)
    with source.open("rb") as image:
        if provider == "nvidia":
            response = client.images.edit(model=model, image=image, prompt=prompt)
        else:
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


def _has_env(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def _resolve_provider(provider: str | None) -> str:
    selected = (provider or os.getenv("IMAGE_PROVIDER", "auto")).lower()
    if selected != "auto":
        return selected
    if _has_env("OPENAI_API_KEY"):
        return "openai"
    return "local"


def _sharpness_score(path: Path) -> float:
    try:
        from PIL import Image, ImageStat
    except ImportError:
        return MIN_SHARPNESS_SCORE

    image = Image.open(path).convert("L").resize((195, 422))
    pixels = image.load()
    edges = []
    for y in range(1, image.height - 1):
        for x in range(1, image.width - 1):
            gx = int(pixels[x + 1, y]) - int(pixels[x - 1, y])
            gy = int(pixels[x, y + 1]) - int(pixels[x, y - 1])
            edges.append(abs(gx) + abs(gy))
    return float(ImageStat.Stat(Image.new("L", (1, 1))).mean[0]) if not edges else sum(edges) / len(edges)


def _looks_deck_ready(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 20_000:
        return False
    try:
        from PIL import Image
    except ImportError:
        return True

    image = Image.open(path).convert("RGB")
    if image.width < 360 or image.height < 700:
        return False
    extrema = image.getextrema()
    if all(high - low <= 8 for low, high in extrema):
        return False
    return _sharpness_score(path) >= MIN_SHARPNESS_SCORE


def _render_local_concept(source: Path, page: dict[str, Any], output: Path) -> None:
    """Render a deterministic, readable concept without an image-generation API."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: pip install -r requirements.txt") from exc

    image = base64.b64encode(source.read_bytes()).decode("ascii")
    page_name = page.get("page_name", "Mobile screen")
    path_name = unquote(urlparse(page.get("url", "")).path.rstrip("/").split("/")[-1])
    product_name = " ".join(path_name.replace("-", " ").split()).title() if path_name else page_name
    is_cart = page_name.lower() == "cart" or "/cart" in page.get("url", "")
    is_collection = "collection" in page_name.lower() or "/collections/" in page.get("url", "")
    heading = "Your bag" if is_cart else ("Shop the edit" if is_collection else product_name)
    supporting = "Review your selections before checkout" if is_cart else (
        "Curated pieces, easier to scan" if is_collection else "Details, delivery and styling in one place"
    )
    heading = html.escape(heading)
    supporting = html.escape(supporting)
    module = (
        '<div class="cart-card"><div><b>Order summary</b><small>Review items and continue securely</small></div><strong>View bag</strong></div>'
        if is_cart else
        '<div class="collection-tools"><span>New in</span><span>Filter</span><span>Sort</span></div>'
        if is_collection else
        '<div class="product-tools"><span>Details</span><span>Delivery</span><span>Returns</span></div>'
    )
    cta_label = "Continue to checkout" if is_cart else ("Explore collection" if is_collection else "Add to bag")
    cta_label = html.escape(cta_label)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            browser_page = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            browser_page.set_content(
                f"""<!doctype html>
<html><head><style>
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: 390px; height: 844px; overflow: hidden; background: #f7f4ef; font-family: Arial, sans-serif; }}
.screen {{ position: relative; width: 390px; height: 844px; overflow: hidden; background: #f7f4ef; }}
.source {{ width: 100%; height: 100%; object-fit: cover; object-position: top center; display: block; }}
.veil {{ position: absolute; inset: 0; pointer-events: none; background: linear-gradient(180deg, transparent 53%, rgba(20, 18, 18, .04) 65%, rgba(20, 18, 18, .40) 100%); }}
.panel {{ position: absolute; left: 0; right: 0; top: 545px; bottom: 0; padding: 17px 16px 78px; background: #f7f4ef; color: #30292b; border-radius: 18px 18px 0 0; box-shadow: 0 -8px 24px rgba(20,18,18,.08); }}
.eyebrow {{ margin: 0 0 6px; color: #b94f47; font-size: 8px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; }}
.panel h1 {{ margin: 0 0 5px; font-size: 18px; line-height: 1.12; letter-spacing: -.2px; }}
.panel p {{ margin: 0 0 12px; color: #6a6066; font-size: 10px; line-height: 1.25; }}
.product-tools, .collection-tools {{ display: flex; gap: 7px; }}
.product-tools span, .collection-tools span {{ padding: 8px 11px; border: 1px solid #e5d9d1; border-radius: 999px; background: #fffaf5; color: #4e4546; font-size: 9px; }}
.collection-tools span:nth-child(2), .product-tools span:nth-child(2) {{ background: #30292b; border-color: #30292b; color: white; }}
.cart-card {{ display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid #e5d9d1; border-radius: 10px; background: #fffaf5; }}
.cart-card b, .cart-card small {{ display: block; }}
.cart-card b {{ font-size: 11px; }}
.cart-card small {{ margin-top: 3px; color: #6a6066; font-size: 9px; }}
.cart-card strong {{ color: #b94f47; font-size: 10px; }}
.trust {{ position: absolute; left: 0; right: 0; bottom: 78px; height: 60px; display: flex; align-items: center; justify-content: space-around; background: #fffaf5; border-top: 1px solid #eadfd6; border-bottom: 1px solid #eadfd6; color: #4e4546; font-size: 9px; text-align: center; }}
.trust span {{ width: 31%; }}
.trust b {{ display: block; color: #b94f47; font-size: 13px; margin-bottom: 2px; }}
.cta {{ position: absolute; left: 12px; right: 12px; bottom: 12px; height: 54px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-radius: 8px; background: #30292b; color: white; font-size: 13px; font-weight: 700; box-shadow: 0 5px 18px rgba(20,18,18,.22); }}
.cta em {{ color: #f2c9bd; font-size: 10px; font-style: normal; font-weight: 400; }}
</style></head><body><main class="screen">
<img class="source" src="data:image/png;base64,{image}" alt="Existing {page_name} screen">
<div class="veil"></div>
<section class="panel"><div class="eyebrow">{html.escape(page_name)}</div><h1>{heading}</h1><p>{supporting}</p>{module}</section>
<div class="trust"><span><b>01</b>Easy returns</span><span><b>02</b>Secure checkout</span><span><b>03</b>Fast delivery</span></div>
<div class="cta"><span>{cta_label} <em>Designed for mobile</em></span><span>-></span></div>
</main></body></html>"""
            )
            browser_page.screenshot(path=str(output), full_page=False)
        finally:
            browser.close()


def _screen_filename(index: int, page_name: str) -> str:
    safe_name = re.sub(r"[^a-z0-9]+", "-", page_name.lower()).strip("-") or "screen"
    return f"{index + 1:02d}-{safe_name}-proposed.png"


def uplift_audit(
    audit: dict[str, Any],
    output_dir: str | Path,
    max_screens: int | None = None,
    provider: str | None = None,
    page_filter: str | None = None,
) -> dict[str, Any]:
    """Generate proposed screens and attach their non-destructive paths to audit JSON."""
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    requested_provider = (provider or os.getenv("IMAGE_PROVIDER", "auto")).lower()
    selected_provider = _resolve_provider(provider)
    model = os.getenv(
        "NVIDIA_IMAGE_MODEL" if selected_provider == "nvidia" else "OPENAI_IMAGE_MODEL",
        "black-forest-labs/flux.1-dev" if selected_provider == "nvidia" else "gpt-image-1",
    )
    selected = [page for page in audit.get("pages", []) if page.get("screenshot_path")]
    if page_filter:
        selected = [page for page in selected if page.get("page_name", "").lower() == page_filter.lower()]
    selected.sort(key=lambda page: (page.get("priority") != "P0", page.get("priority") != "P1"))

    generated = 0
    for index, page in enumerate(selected):
        if max_screens is not None and generated >= max_screens:
            break
        source = Path(page["screenshot_path"])
        if not source.is_file():
            continue
        destination = target / _screen_filename(index, page.get("page_name", "screen"))
        if selected_provider == "local":
            _render_local_concept(source, page, destination)
            page["proposed_image_provider"] = "local"
        else:
            prompt = (
                build_text_to_image_prompt(audit, page)
                if selected_provider == "nvidia"
                else build_uplift_prompt(audit, page)
            )
            try:
                _edit_image(source, prompt, destination, model, selected_provider)
                if selected_provider == "nvidia" and not _looks_deck_ready(destination):
                    if requested_provider != "auto":
                        raise RuntimeError(
                            "NVIDIA returned an unusable proposed image. "
                            "Use a supported NVIDIA image model or set --provider openai."
                        )
                    _render_local_concept(source, page, destination)
                    page["proposed_image_provider"] = "local-fallback-after-nvidia"
                else:
                    page["proposed_image_provider"] = selected_provider
            except RuntimeError:
                if requested_provider != "auto" or os.getenv("STRICT_IMAGE_PROVIDER", "").strip() == "1":
                    raise
                _render_local_concept(source, page, destination)
                page["proposed_image_provider"] = f"local-fallback-after-{requested_provider}"
        page["proposed_screenshot_path"] = str(destination)
        generated += 1
    if not generated:
        raise RuntimeError("No real Playwright screenshots found in this audit. Run `audit` or `demo` first.")
    return audit


def load_and_uplift(
    audit_path: str | Path,
    output_dir: str | Path,
    max_screens: int | None = None,
    provider: str | None = None,
    page_filter: str | None = None,
) -> None:
    source = Path(audit_path)
    audit = json.loads(source.read_text(encoding="utf-8"))
    updated = uplift_audit(audit, output_dir, max_screens, provider, page_filter)
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
