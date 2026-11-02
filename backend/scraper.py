"""Fetch a URL's full readable text — port of AIST-Forge's `fetch_url` tool.

HTML → body text minus boilerplate tags; PDFs → PyMuPDF text; a bot-check
interstitial (CAPTCHA / "just a moment") raises instead of passing junk on.
"""

from __future__ import annotations

import asyncio

import pymupdf as fitz
import httpx
from bs4 import BeautifulSoup

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_STRIP_TAGS = ("script", "style", "noscript", "nav", "header", "footer", "aside", "form")
_BOT_CHECK_PHRASES = (
    "checking your browser", "just a moment...", "verify you are human",
    "are you a robot", "captcha", "attention required", "unusual traffic",
    "access denied", "enable javascript and cookies to continue",
)
DEFAULT_MAX_CHARS = 24_000


class FetchError(Exception):
    pass


async def fetch_url(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict:
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
        ) as c:
            r = await c.get(url)
            r.raise_for_status()
    except httpx.HTTPError as e:
        raise FetchError(f"Could not fetch {url}: {type(e).__name__} {e}") from e

    ctype = r.headers.get("content-type", "").lower()
    if "pdf" in ctype or r.content.startswith(b"%PDF-"):
        title, text = None, await asyncio.to_thread(_pdf_text, r.content, max_chars)
    elif "html" in ctype:
        title, text = _html_text(r.text)
        if len(text) < 2000 and any(p in f"{title or ''}\n{text}".lower() for p in _BOT_CHECK_PHRASES):
            raise FetchError(f"{r.url.host} served a bot check instead of the page")
    else:
        title, text = None, r.text

    return {
        "url": str(r.url),
        "title": title,
        "content": text[:max_chars],
        "truncated": len(text) > max_chars,
    }


def _html_text(html: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    for tag in soup(_STRIP_TAGS):
        tag.decompose()
    body = soup.body or soup
    lines = (ln.strip() for ln in body.get_text("\n").splitlines())
    return title, "\n".join(ln for ln in lines if ln)


def _pdf_text(data: bytes, limit: int) -> str:
    pages, size = [], 0
    with fitz.open(stream=data, filetype="pdf") as doc:
        for page in doc:
            t = page.get_text("text")
            pages.append(t)
            size += len(t)
            if size > limit:
                break
    return "\n\n".join(pages)
