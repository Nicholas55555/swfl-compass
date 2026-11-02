"""Capture feature screenshots for the deck/README (no video).

Covers what the main demo doesn't: the student persona, a RAG follow-up with the
agent's tool steps expanded, a generated guide, and the app on a phone.
App must be running.  backend/.venv/Scripts/python scripts/capture_features.py
"""

from __future__ import annotations

import asyncio

from playwright.async_api import Page, async_playwright

from record_demo import OUT, URL, scroll_to

LAST = "() => [...document.querySelectorAll('.msg.assistant')].at(-1)"


async def ask(page: Page, text: str) -> None:
    box = page.get_by_placeholder("Ask about hurricanes")
    await box.fill(text)
    await box.press("Enter")
    await page.wait_for_function(f"() => ({LAST})()?.querySelector('.suggestions')", timeout=200_000)
    await asyncio.sleep(1.5)


async def shot(page: Page, name: str) -> None:
    await page.screenshot(path=str(OUT / f"{name}.png"))
    print("shot", name)


async def main() -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()

        # ── Desktop: student persona → question → RAG follow-up → guide
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()
        await page.goto(URL)
        await page.wait_for_selector(".welcome")
        await page.get_by_role("button", name="🎓 I study here").click()
        await asyncio.sleep(1)
        await shot(page, "12-student-welcome")

        await ask(page, "Where can FGCU students find affordable housing near campus?")
        await ask(page, "Which of those are closest to campus, and what do they cost?")
        # expand the finished turn's agent steps
        await page.locator(".msg.assistant").last.locator(".steps summary").click()
        await asyncio.sleep(0.8)
        await scroll_to(page, ".msg.assistant")
        await asyncio.sleep(1)
        await shot(page, "13-followup-rag-steps")

        await page.get_by_role("button", name="📄 Make a guide").click()
        await page.locator(".builder input").fill("a move-in checklist for FGCU students renting off campus")
        await asyncio.sleep(0.5)
        await shot(page, "14-guide-builder")
        await page.get_by_role("button", name="Write my guide").click()
        await page.wait_for_function(f"() => ({LAST})()?.querySelector('.doc') && ({LAST})()?.querySelector('.suggestions')", timeout=240_000)
        await asyncio.sleep(1)
        await scroll_to(page, ".doc")
        await asyncio.sleep(1)
        await shot(page, "15-guide-doc")
        await ctx.close()

        # ── Phone: visitor question with places → answer + map
        m = await browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        mp = await m.new_page()
        await mp.goto(URL)
        await mp.wait_for_selector(".welcome")
        await mp.get_by_role("button", name="🌴 I'm visiting").click()
        await ask(mp, "Where can I see manatees near Fort Myers?")
        await scroll_to(mp, ".msg.assistant", offset=70)
        await asyncio.sleep(1)
        await shot(mp, "16-mobile-answer")
        if await mp.locator(".places").count():
            await scroll_to(mp, ".places", offset=70)
            await asyncio.sleep(3)
            await shot(mp, "17-mobile-map")
        await m.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
