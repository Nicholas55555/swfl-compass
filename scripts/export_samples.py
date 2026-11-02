"""Generate sample outputs from the running app into docs/samples/.

Calls the real backend (http://localhost:8010) the same way the UI does, then saves each
result as Markdown plus a PDF rendered with the same styling as the app's
"Print / Save PDF" button (Playwright → Chromium PDF).

Usage (app running):  backend/.venv/Scripts/python scripts/export_samples.py
Re-render the PDFs from the saved .md files only (no API calls):  ... export_samples.py --pdf-only
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import date
from pathlib import Path

import httpx
import markdown
from playwright.async_api import async_playwright

API = "http://localhost:8010"
OUT = Path(__file__).resolve().parent.parent / "docs" / "samples"

SAMPLES = [
    {
        "slug": "itinerary-3-day-fort-myers-family",
        "kind": "Itinerary",
        "label": "🗺️ Plan a 3-day itinerary based in Fort Myers — Beaches, Nature & wildlife, Family / kids",
        "persona": "visitor",
        "task": {"kind": "itinerary", "days": 3, "base": "Fort Myers", "interests": ["Beaches", "Nature & wildlife", "Family / kids"], "notes": "visiting in March with two kids"},
    },
    {
        "slug": "guide-hurricane-prep-renters-lee-county",
        "kind": "Guide",
        "label": "📄 Make me a guide: hurricane preparation for renters in Lee County",
        "persona": "resident",
        "task": {"kind": "guide", "topic": "hurricane preparation for renters in Lee County"},
    },
    {
        "slug": "answer-fgcu-to-downtown-without-car",
        "kind": "Chat answer",
        "label": "How do I get from FGCU to downtown Fort Myers without a car?",
        "persona": "student",
        "task": None,
    },
]
SUMMARY_URL = "https://myfwc.com/research/redtide/statewide/"

PDF_CSS = """
body{font-family:"Segoe UI",system-ui,sans-serif;max-width:760px;margin:0 auto;padding:0 8px;color:#12302c;line-height:1.55;font-size:13px}
h1{color:#00885a;border-bottom:3px solid #00885a;padding-bottom:6px;font-size:24px}
h2{color:#0b5ea8;margin-top:24px;font-size:18px} h3{font-size:15px}
a{color:#0b5ea8} li{margin:3px 0} table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid #d5e3df;padding:5px 7px;text-align:left;vertical-align:top} th{background:#eef7f3}
.meta{font-size:11px;color:#5d7570;margin-bottom:14px}
.foot{margin-top:32px;font-size:10px;color:#5d7570;border-top:1px solid #ddd;padding-top:6px}
"""


async def run_chat(client: httpx.AsyncClient, sample: dict) -> dict:
    body = {
        "session_id": str(uuid.uuid4()),
        "persona": sample["persona"],
        "messages": [{"role": "user", "content": sample["label"]}],
        "task": sample["task"],
    }
    result = {"steps": [], "answer": "", "places": [], "resources": [], "suggested_questions": []}
    async with client.stream("POST", f"{API}/api/chat", json=body, timeout=300) as r:
        r.raise_for_status()
        async for line in r.aiter_lines():
            if not line.startswith("data: "):
                continue
            ev = json.loads(line[6:])
            if ev["type"] == "status":
                result["steps"].append(ev["text"])
            elif ev["type"] == "answer":
                result["answer"] = ev["text"]
            elif ev["type"] == "places":
                result["places"] = ev["places"]
            elif ev["type"] == "extras":
                result["resources"] = ev.get("resources", [])
                result["suggested_questions"] = ev.get("suggested_questions", [])
            elif ev["type"] == "error":
                raise RuntimeError(ev["text"])
    return result


def to_markdown(sample: dict, res: dict) -> str:
    parts = [
        f"<!-- SWFL Compass sample output · {sample['kind']} · generated {date.today():%B %d, %Y} -->",
        f"> **Prompt** ({sample['persona']}): {sample['label']}",
        "",
        res["answer"].strip(),
    ]
    if res["places"]:
        parts += ["", "## Verified places (Google Maps)", "", "| # | Place | Rating | Address | Map |", "|---|---|---|---|---|"]
        for i, p in enumerate(res["places"], 1):
            rating = f"★ {p['rating']:.1f} ({p.get('reviews') or 0:,})" if p.get("rating") else ""
            parts.append(f"| {i} | {p['name']} | {rating} | {p.get('address', '')} | [Open]({p.get('maps_url', '')}) |")
    if res["resources"]:
        parts += ["", "## Helpful resources", ""]
        parts += [f"- [{r['title']}]({r['url']}): {r.get('why', '')}" for r in res["resources"]]
    if res["suggested_questions"]:
        parts += ["", "## You might also ask", ""]
        parts += [f"- {q}" for q in res["suggested_questions"]]
    parts += ["", "<details><summary>Agent steps</summary>", ""]
    parts += [f"- {s}" for s in res["steps"]]
    parts += ["", "</details>", ""]
    return "\n".join(parts)


def to_html(title: str, md_text: str) -> str:
    body = markdown.markdown(md_text, extensions=["tables", "sane_lists"])
    # GitHub-style task lists (- [ ] item) aren't part of python-markdown
    body = body.replace("<li>[ ] ", "<li>☐ ").replace("<li>[x] ", "<li>☑ ")
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
        f"<style>{PDF_CSS}</style></head><body>{body}"
        f"<div class='foot'>Generated by SWFL Compass · {date.today():%B %d, %Y} · "
        "AI-generated: verify hours, prices and safety information with official sources.</div></body></html>"
    )


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient() as client, async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()

        async def save(slug: str, title: str, md_text: str) -> None:
            (OUT / f"{slug}.md").write_text(md_text, encoding="utf-8")
            await page.set_content(to_html(title, md_text), wait_until="load")
            await page.pdf(path=str(OUT / f"{slug}.pdf"), format="Letter", print_background=True,
                           margin={"top": "0.6in", "bottom": "0.6in", "left": "0.6in", "right": "0.6in"})
            print("saved", slug)

        if "--pdf-only" in sys.argv:
            for md_file in sorted(OUT.glob("*.md")):
                await save(md_file.stem, md_file.stem, md_file.read_text(encoding="utf-8"))
            await browser.close()
            return

        for sample in SAMPLES:
            res = await run_chat(client, sample)
            (OUT / f"{sample['slug']}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
            await save(sample["slug"], sample["label"], to_markdown(sample, res))

        r = await client.post(f"{API}/api/summarize", json={"url": SUMMARY_URL, "focus": "Is there red tide in Southwest Florida right now?"}, timeout=120)
        r.raise_for_status()
        s = r.json()
        md_text = (
            f"<!-- SWFL Compass sample output · Resource summary · generated {date.today():%B %d, %Y} -->\n"
            f"# Summary: {s.get('title') or SUMMARY_URL}\n\n> **Source:** <{s['url']}>\n\n{s['summary'].strip()}\n"
        )
        await save("summary-fwc-red-tide-status", "FWC red tide status summary", md_text)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
