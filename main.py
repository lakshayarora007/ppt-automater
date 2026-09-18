import argparse
import json
from pathlib import Path

from app.audit import run_audit
from app.crawler import crawl_site
from app.insights import analyze_pages
from app.ppt_builder import build_pptx_from_audit
from app.ui_uplift import load_and_uplift
from app.ui_uplift import collect_chatgpt_results, prepare_chatgpt_handoff


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run_audit(url: str, brand: str, output: str):
    out_path = Path(output)
    snap = crawl_site(url, max_pages=8, screenshot_dir=out_path.parent / "screenshots")
    if snap:
        audit = analyze_pages(url, snap)
        audit.brand_name = brand
        source = f"Pages crawled: {len(snap)}"
    else:
        print("No pages could be retrieved; generating a clearly labelled heuristic audit.")
        audit = run_audit(url=url, brand_name=brand)
        source = "Pages crawled: 0 (heuristic fallback)"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(audit.model_dump(mode="json"), indent=2), encoding="utf-8")
    print(f"Audit saved to: {out_path}")
    print(source)


def _run_ppt(input_path: str, output: str):
    data = _load_json(input_path)
    ppt_path = Path(output)
    ppt_path.parent.mkdir(parents=True, exist_ok=True)
    build_pptx_from_audit(data, str(ppt_path))
    print(f"PPT saved to: {ppt_path}")


def _run_uplift(input_path: str, output_dir: str, max_screens: int):
    load_and_uplift(input_path, output_dir, max_screens)
    print(f"Proposed screens saved to: {output_dir}")


def _prepare_chatgpt(input_path: str, jobs_dir: str, max_screens: int):
    count = prepare_chatgpt_handoff(input_path, jobs_dir, max_screens)
    print(f"Created {count} ChatGPT uplift jobs in: {jobs_dir}")
    print("Open each job, upload current-screen.png in your already signed-in ChatGPT browser, paste prompt.txt, then save its result as proposed.png in the same job folder.")


def _collect_chatgpt(jobs_dir: str):
    count = collect_chatgpt_results(jobs_dir)
    print(f"Attached {count} proposed screens to the audit JSON.")


def _run_demo(url: str, brand: str):
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    audit_path = output_dir / "demo-audit.json"
    ppt_path = output_dir / "demo-cro-pitch.pptx"
    _run_audit(url=url, brand=brand, output=str(audit_path))
    _run_ppt(str(audit_path), str(ppt_path))


def build_parser():
    parser = argparse.ArgumentParser(description="CRO pitch audit generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Run a CRO audit for a URL")
    audit.add_argument("--url", required=True)
    audit.add_argument("--brand", default="Brand")
    audit.add_argument("--output", default="output/audit.json")

    ppt = subparsers.add_parser("ppt", help="Generate PPT from an audit JSON file")
    ppt.add_argument("--input", required=True)
    ppt.add_argument("--output", default="output/cro-pitch.pptx")

    uplift = subparsers.add_parser("uplift", help="Generate proposed UI screens from real Playwright screenshots")
    uplift.add_argument("--input", required=True, help="Audit JSON created by the audit or demo command")
    uplift.add_argument("--output-dir", default="output/proposed-screens")
    uplift.add_argument("--max-screens", type=int, default=3)

    prepare = subparsers.add_parser("prepare-chatgpt", help="Prepare upload/prompt jobs for a user-controlled ChatGPT image-edit session")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--jobs-dir", default="output/chatgpt-uplift-jobs")
    prepare.add_argument("--max-screens", type=int, default=3)

    collect = subparsers.add_parser("collect-chatgpt", help="Attach downloaded ChatGPT proposed screens to the audit")
    collect.add_argument("--jobs-dir", default="output/chatgpt-uplift-jobs")

    demo = subparsers.add_parser("demo", help="Run demo audit + PPT flow")
    demo.add_argument("--url", required=True)
    demo.add_argument("--brand", default="Brand")

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "audit":
        _run_audit(url=args.url, brand=args.brand, output=args.output)
    elif args.command == "ppt":
        _run_ppt(input_path=args.input, output=args.output)
    elif args.command == "uplift":
        _run_uplift(input_path=args.input, output_dir=args.output_dir, max_screens=args.max_screens)
    elif args.command == "prepare-chatgpt":
        _prepare_chatgpt(input_path=args.input, jobs_dir=args.jobs_dir, max_screens=args.max_screens)
    elif args.command == "collect-chatgpt":
        _collect_chatgpt(jobs_dir=args.jobs_dir)
    elif args.command == "demo":
        _run_demo(url=args.url, brand=args.brand)
