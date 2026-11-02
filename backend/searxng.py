"""SearXNG client — Docker lifecycle + paced HTML-scrape search.

Replicates AIST-Forge's `app/services/searxng.py`: discover or start a SearXNG
container on a random host port, wait for /healthz, then scrape `/search`
(HTML, so no `format=json` settings change is needed). Searches are paced
app-wide because rapid-fire queries get upstream engines to CAPTCHA us.

Everything it needs lives in this repo's `searxng/` folder: `settings.yml` (mounted
read-only) and, optionally, `searxng-image.tar` (a saved copy of the pinned image, so
it runs offline / without Docker Hub). Image source order: local → tarball → pull.

Set SEARXNG_BASE_URL to skip Docker and use an existing instance (e.g. docker compose).
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

CONTAINER_PORT = "8080/tcp"
IMAGE_TAG = os.getenv("SEARXNG_IMAGE", "searxng/searxng:2025.7.19-b95a3e9")  # pinned
CONTAINER_NAME = os.getenv("SEARXNG_CONTAINER", "swfl-compass-searxng")
SEARXNG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "searxng")
SETTINGS_FILE = os.path.join(SEARXNG_DIR, "settings.yml")
TARBALL = os.path.join(SEARXNG_DIR, "searxng-image.tar")
MIN_INTERVAL = float(os.getenv("SEARCH_MIN_INTERVAL", "2.0"))
SNIPPET_MAX = 600

# Mozilla UA bypasses SearXNG's bot detection for HTML responses.
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class SearXNGNotAvailableError(RuntimeError):
    pass


class SearXNGClient:
    def __init__(self) -> None:
        self.base_url: str | None = os.getenv("SEARXNG_BASE_URL") or None
        self._lock: asyncio.Lock | None = None
        self._last: float | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────
    def ensure_running(self, wait_seconds: float = 30.0) -> str:
        if self.base_url:
            return self.base_url
        import docker
        import docker.errors

        try:
            client = docker.from_env()
        except docker.errors.DockerException as e:
            raise SearXNGNotAvailableError(f"Docker not reachable: {e}") from e

        try:
            client.images.get(IMAGE_TAG)
        except docker.errors.ImageNotFound:
            if os.path.exists(TARBALL):
                with open(TARBALL, "rb") as fh:
                    client.images.load(fh.read())
            try:
                client.images.get(IMAGE_TAG)
            except docker.errors.ImageNotFound:
                client.images.pull(IMAGE_TAG)

        existing = client.containers.list(all=True, filters={"name": CONTAINER_NAME})
        container = existing[0] if existing else client.containers.run(
            IMAGE_TAG,
            detach=True,
            name=CONTAINER_NAME,
            ports={CONTAINER_PORT: None},
            volumes={SETTINGS_FILE: {"bind": "/etc/searxng/settings.yml", "mode": "ro"}},
            dns=["1.1.1.1", "8.8.8.8"],  # venue Wi-Fi DNS flakes inside Docker
        )
        if container.status != "running":
            container.start()

        deadline = time.monotonic() + 10
        mapping = None
        while time.monotonic() < deadline:
            container.reload()
            mapping = (container.attrs.get("NetworkSettings", {}).get("Ports") or {}).get(
                CONTAINER_PORT
            )
            if mapping:
                break
            time.sleep(0.3)
        if not mapping:
            raise SearXNGNotAvailableError("SearXNG container published no host port")

        url = f"http://localhost:{mapping[0]['HostPort']}"
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{url}/healthz", timeout=2).status_code == 200:
                    self.base_url = url
                    return url
            except Exception:
                pass
            time.sleep(0.5)
        raise SearXNGNotAvailableError(f"SearXNG didn't respond at {url}")

    # ── Search ─────────────────────────────────────────────────────────
    async def search(self, query: str, max_results: int = 6) -> list[dict[str, Any]]:
        # No retry here: on empty results the agent falls back to Google grounding.
        return await self._search_once(query, max_results)

    async def _search_once(self, query: str, max_results: int) -> list[dict[str, Any]]:
        if not self.base_url:
            await asyncio.to_thread(self.ensure_running)
        if self._lock is None:
            self._lock = asyncio.Lock()
        async with self._lock:
            if self._last is not None:
                wait = MIN_INTERVAL - (time.monotonic() - self._last)
                if wait > 0:
                    await asyncio.sleep(wait)
            try:
                async with httpx.AsyncClient(
                    timeout=12, headers={"User-Agent": _USER_AGENT}
                ) as c:
                    r = await c.get(f"{self.base_url}/search", params={"q": query})
                    r.raise_for_status()
                    return _parse_results(r.text, max_results)
            finally:
                self._last = time.monotonic()


def _parse_results(html: str, max_results: int) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict[str, Any]] = []
    for r in soup.select(".result"):
        title_el = r.select_one("h3 a") or r.select_one("h2 a") or r.select_one(".result__a")
        if not title_el:
            continue
        snippet_el = (
            r.select_one("p.content") or r.select_one(".result-content") or r.select_one(".result__snippet")
        )
        out.append(
            {
                "title": " ".join(title_el.get_text(" ", strip=True).split()),
                "url": title_el.get("href", ""),
                "snippet": " ".join(snippet_el.get_text(" ", strip=True).split())[:SNIPPET_MAX] if snippet_el else "",
            }
        )
        if len(out) >= max_results:
            break
    return out


searxng = SearXNGClient()
