"""Record the SWFL Compass demo video + screenshots with Playwright.

Drives the real running app (backend :8010 + frontend :5173 must be up):
persona → question → live agent steps → answer + map + resources → summarize →
itinerary builder → generated itinerary document with map.

Usage (from repo root):
  backend/.venv/Scripts/python -m pip install playwright imageio-ffmpeg
  backend/.venv/Scripts/python -m playwright install chromium
  backend/.venv/Scripts/python scripts/record_demo.py
Outputs: docs/demo/*.png and docs/demo/raw/*.webm (converted by make_video.py).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import Page, async_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo"
RAW = OUT / "raw"
URL = "http://localhost:5173/"
W, H = 1280, 800


async def smooth_scroll(page: Page, total: int, step: int = 60, delay: float = 0.03) -> None:
    for _ in range(max(1, total // step)):
        await page.mouse.wheel(0, step)
        await asyncio.sleep(delay)


async def scroll_to(page: Page, selector: str, offset: int = 90) -> None:
    """Smoothly scroll the LAST `selector` to just below the sticky header."""
    await page.evaluate(
        "([s, o]) => { const e = [...document.querySelectorAll(s)].at(-1); if (!e) return;"
        " window.scrollTo({ top: window.scrollY + e.getBoundingClientRect().top - o, behavior: 'smooth' }) }",
        [selector, offset],
    )
    await asyncio.sleep(1.2)


async def shot(page: Page, name: str) -> None:
    await page.screenshot(path=str(OUT / f"{name}.png"))
    print("shot", name)


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
            record_video_dir=str(RAW),
            record_video_size={"width": W, "height": H},
        )
        page = await ctx.new_page()
        page.set_default_timeout(150_000)

        # 1. Welcome + persona
        await page.goto(URL)
        await page.wait_for_selector(".welcome")
        await asyncio.sleep(1.5)
        await shot(page, "01-welcome")
        await page.get_by_role("button", name="🌴 I'm visiting").click()
        await asyncio.sleep(1.2)

        # 2. Ask a question (typed, so the video shows it)
        box = page.get_by_placeholder("Ask about hurricanes")
        await box.click()
        await box.press_sequentially("What are the best beaches near Naples, and is there red tide right now?", delay=45)
        await asyncio.sleep(0.6)
        await box.press("Enter")
        await page.wait_for_selector(".steps li")
        await asyncio.sleep(2.5)
        await shot(page, "02-agent-steps")

        # 3. Answer, map, resources, follow-ups
        await page.wait_for_selector(".msg.assistant .answer", timeout=150_000)
        await page.wait_for_selector(".suggestions", timeout=120_000)
        await asyncio.sleep(1.5)
        await scroll_to(page, ".msg.assistant")
        await asyncio.sleep(1.5)
        await shot(page, "03-answer")
        if await page.locator(".places").count():
            await scroll_to(page, ".places")
            await asyncio.sleep(2.5)  # let map tiles load
            await shot(page, "04-map")
        await scroll_to(page, ".resources")
        await asyncio.sleep(1.5)

        # 4. Summarize a resource (if the answer came with any)
        if await page.locator(".resource").count():
            await page.locator(".resource button", has_text="Summarize").first.click()
            await page.wait_for_selector(".summary", timeout=90_000)
            await asyncio.sleep(1.5)
            await scroll_to(page, ".resources")
            await asyncio.sleep(1.5)
            await shot(page, "05-resources-summary")
        await scroll_to(page, ".suggestions", offset=300)
        await asyncio.sleep(2)
        await shot(page, "06-followups")

        # 5. Itinerary builder
        await page.get_by_role("button", name="🗺️ Plan an itinerary").click()
        await asyncio.sleep(1)
        await page.locator(".builder select").first.select_option("2")
        await page.locator(".builder select").nth(1).select_option("Naples")
        for interest in ("🏖️ Beaches", "🍤 Food", "🐊 Nature & wildlife"):
            await page.get_by_role("button", name=interest).click()
            await asyncio.sleep(0.4)
        await page.locator(".builder input").fill("Visiting in March")
        await asyncio.sleep(1)
        await shot(page, "07-itinerary-builder")
        await page.get_by_role("button", name="Build my itinerary").click()
        await page.wait_for_selector(".doc", timeout=200_000)
        await page.wait_for_function(
            "() => [...document.querySelectorAll('.msg.assistant')].at(-1).querySelector('.suggestions')",
            timeout=120_000,
        )
        await asyncio.sleep(1)
        await scroll_to(page, ".doc")
        await asyncio.sleep(2)
        await shot(page, "08-itinerary-doc")
        await smooth_scroll(page, 900, step=40, delay=0.04)
        await asyncio.sleep(1)
        await shot(page, "09-itinerary-days")
        if await page.locator(".places").count() > 1:
            await scroll_to(page, ".places")
            await asyncio.sleep(3)
            await shot(page, "10-itinerary-map")
        await asyncio.sleep(1.5)

        video = page.video
        await ctx.close()  # finalizes the video file
        print("video", await video.path())

        # 6. Mobile screenshot (no video)
        m = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
        mp = await m.new_page()
        await mp.goto(URL)
        await mp.wait_for_selector(".welcome")
        await asyncio.sleep(1)
        await mp.screenshot(path=str(OUT / "11-mobile.png"))
        await m.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
