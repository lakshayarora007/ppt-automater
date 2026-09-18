from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urldefrag, urljoin, urlparse, urlunparse

import requests
from playwright.sync_api import Page, sync_playwright


MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)


@dataclass
class PageSnapshot:
    name: str
    url: str
    title: str
    text: str
    page_type: str = "other"
    screenshot_path: str | None = None


def _normalise_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def _same_site(candidate: str, root: str) -> bool:
    return urlparse(candidate).netloc == urlparse(root).netloc


def _page_type(url: str) -> str:
    path = urlparse(url).path.lower().rstrip("/") or "/"
    if path == "/":
        return "homepage"
    if "/products/" in path:
        return "pdp"
    if "/collections/" in path or path == "/collections":
        return "collection"
    if path == "/cart":
        return "cart"
    if path == "/search":
        return "search"
    if any(term in path for term in ("faq", "shipping", "return", "about", "contact")):
        return "trust"
    return "other"


def _page_name(page_type: str) -> str:
    return {
        "homepage": "Homepage", "pdp": "Product Detail Page", "collection": "Collection Page",
        "cart": "Cart", "search": "Search", "trust": "Trust / Information Page",
    }.get(page_type, "Store Page")


def _candidate_priority(url: str) -> tuple[int, str]:
    kind = _page_type(url)
    return ({"homepage": 0, "collection": 1, "pdp": 2, "cart": 3, "search": 4, "trust": 5}.get(kind, 9), url)


def _clean_candidates(hrefs: Iterable[str], root: str, limit: int) -> list[str]:
    candidates: list[str] = []
    ignored = ("/account", "/policies", "/blogs", "/challenge", "/cdn/", "/password")
    for href in hrefs:
        candidate, _ = urldefrag(urljoin(root + "/", href))
        candidate = _normalise_url(candidate)
        if not _same_site(candidate, root) or candidate == root or any(x in candidate.lower() for x in ignored):
            continue
        if candidate not in candidates:
            candidates.append(candidate)
    ordered = sorted(candidates, key=_candidate_priority)
    # A deck needs a representative funnel, not seven collection links. Keep a
    # small quota per template type, then use the remaining slots if available.
    quotas = {"collection": 2, "pdp": 3, "cart": 1, "search": 1, "trust": 1, "other": 1}
    selected: list[str] = []
    for candidate in ordered:
        kind = _page_type(candidate)
        if quotas.get(kind, 1) > 0:
            selected.append(candidate)
            quotas[kind] = quotas.get(kind, 1) - 1
        if len(selected) == limit:
            return selected
    for candidate in ordered:
        if candidate not in selected:
            selected.append(candidate)
        if len(selected) == limit:
            break
    return selected


def _snapshot_from_page(page: Page, url: str, screenshot_path: str | None = None) -> PageSnapshot:
    try:
        title = (page.title() or "").strip()
    except Exception:
        title = ""
    try:
        text = (page.locator("body").inner_text(timeout=10_000) or "").strip()
    except Exception:
        text = ""
    kind = _page_type(url)
    return PageSnapshot(_page_name(kind), url, title, text, kind, screenshot_path)


def _crawl_with_playwright(root: str, max_pages: int, screenshot_dir: Path | None) -> list[PageSnapshot]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 390, "height": 844}, user_agent=MOBILE_USER_AGENT)
            page = context.new_page()
            page.goto(root, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(1_000)
            home = _capture_snapshot(page, root, 1, screenshot_dir)
            hrefs = page.locator("a[href]").evaluate_all("els => els.map(el => el.href)")
            snapshots = [home]
            for candidate in _clean_candidates(hrefs, root, max_pages - 1):
                try:
                    page.goto(candidate, wait_until="domcontentloaded", timeout=20_000)
                    page.wait_for_timeout(700)
                    snapshots.append(_capture_snapshot(page, candidate, len(snapshots) + 1, screenshot_dir))
                except Exception:
                    continue
            return snapshots
        finally:
            browser.close()


def _capture_snapshot(page: Page, url: str, index: int, screenshot_dir: Path | None) -> PageSnapshot:
    screenshot_path = None
    if screenshot_dir:
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = screenshot_dir / f"{index:02d}-{_page_type(url)}.png"
        page.screenshot(path=str(path), full_page=False)
        screenshot_path = str(path)
    return _snapshot_from_page(page, url, screenshot_path)


def _crawl_with_requests(root: str, max_pages: int) -> list[PageSnapshot]:
    """Best-effort text crawl used where Chromium cannot run."""
    from html.parser import HTMLParser

    class Extractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.links: list[str] = []
            self.parts: list[str] = []
            self.title = ""
            self._in_title = False

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "a":
                href = dict(attrs).get("href")
                if href:
                    self.links.append(href)
            self._in_title = tag == "title"

        def handle_endtag(self, tag: str) -> None:
            if tag == "title":
                self._in_title = False

        def handle_data(self, data: str) -> None:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)
                if self._in_title:
                    self.title += value

    def fetch(url: str) -> tuple[PageSnapshot, list[str]] | None:
        try:
            response = requests.get(url, headers={"User-Agent": MOBILE_USER_AGENT}, timeout=20)
            response.raise_for_status()
        except requests.RequestException:
            return None
        parser = Extractor()
        parser.feed(response.text)
        final_url = _normalise_url(response.url)
        kind = _page_type(final_url)
        return PageSnapshot(_page_name(kind), final_url, parser.title.strip(), " ".join(parser.parts), kind), parser.links

    first = fetch(root)
    if not first:
        return []
    home, hrefs = first
    snapshots = [home]
    for candidate in _clean_candidates(hrefs, root, max_pages - 1):
        result = fetch(candidate)
        if result:
            snapshot, _ = result
            snapshots.append(snapshot)
    return snapshots


def crawl_site(base_url: str, max_pages: int = 8, screenshot_dir: str | Path | None = None) -> list[PageSnapshot]:
    """Crawl representative mobile storefront pages, with a safe HTTP fallback."""
    if max_pages < 1:
        return []
    root = _normalise_url(base_url)
    screenshots = Path(screenshot_dir) if screenshot_dir else None
    try:
        snapshots = _crawl_with_playwright(root, max_pages, screenshots)
        if snapshots:
            return snapshots
    except Exception as exc:
        print(f"Playwright unavailable ({exc.__class__.__name__}); using HTTP fallback.")
    return _crawl_with_requests(root, max_pages)
