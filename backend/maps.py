"""Google Places API (New) — verified, real places for answers and itineraries.

The agent's `find_places` tool calls Text Search and gets back real names, addresses,
ratings, open-now, coordinates and the official Google Maps link. Coordinates feed the
map in the UI (Leaflet + OpenStreetMap tiles, so no extra Maps API is needed there).

Needs GOOGLE_MAPS_API_KEY with "Places API (New)" enabled. Without it the tool reports
that maps are unavailable and the agent carries on with web search.
"""

from __future__ import annotations

import os

import httpx

_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELDS = ",".join(
    f"places.{f}"
    for f in (
        "id",
        "displayName",
        "formattedAddress",
        "location",
        "rating",
        "userRatingCount",
        "googleMapsUri",
        "websiteUri",
        "priceLevel",
        "primaryTypeDisplayName",
        "currentOpeningHours.openNow",
        "editorialSummary",
    )
)
# Bias results to Southwest Florida (Lee/Collier/Charlotte) unless the query says otherwise.
_SWFL_BIAS = {
    "circle": {"center": {"latitude": 26.45, "longitude": -81.85}, "radius": 50000.0}
}
_PRICE = {
    "PRICE_LEVEL_FREE": "Free",
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}


def available() -> bool:
    return bool(os.getenv("GOOGLE_MAPS_API_KEY"))


async def find_places(query: str, max_results: int = 5) -> list[dict]:
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY not set")
    async with httpx.AsyncClient(timeout=12) as c:
        r = await c.post(
            _URL,
            headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": _FIELDS},
            json={"textQuery": query, "maxResultCount": max_results, "locationBias": _SWFL_BIAS},
        )
        r.raise_for_status()
    out = []
    for p in r.json().get("places", []):
        loc = p.get("location") or {}
        out.append(
            {
                "id": p.get("id"),
                "name": (p.get("displayName") or {}).get("text", ""),
                "address": p.get("formattedAddress", ""),
                "lat": loc.get("latitude"),
                "lng": loc.get("longitude"),
                "rating": p.get("rating"),
                "reviews": p.get("userRatingCount"),
                "maps_url": p.get("googleMapsUri"),
                "website": p.get("websiteUri"),
                "price": _PRICE.get(p.get("priceLevel", ""), None),
                "type": (p.get("primaryTypeDisplayName") or {}).get("text"),
                "open_now": (p.get("currentOpeningHours") or {}).get("openNow"),
                "summary": (p.get("editorialSummary") or {}).get("text"),
            }
        )
    return out
