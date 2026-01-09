"""External API clients for geocoding and NASA data.

Provides thin wrappers with timeouts, basic caching, and structured
responses so routes can focus on validation/serialization.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

import requests

DEFAULT_TIMEOUT = 10


class ExternalAPIError(Exception):
    """Raised when an upstream external API responds with an error."""

    def __init__(self, source: str, status_code: Optional[int] = None, message: Optional[str] = None):
        self.source = source
        self.status_code = status_code
        self.message = message or "Upstream request failed"
        super().__init__(f"{source}: {self.message}")


class SimpleTTLCache:
    """Minimal TTL cache to avoid hammering free APIs.
    
    ⚠️  IMPORTANT: This is in-memory only and does NOT persist across process restarts.
    Under multi-worker deployments (gunicorn, uWSGI), each worker has its own cache;
    you could exceed API rate limits if multiple workers hit the same endpoint simultaneously.
    
    For production, consider:
    - Redis-backed cache (flask-caching with Redis backend)
    - Shared cache layer (distributed cache)
    - Request deduplication at gateway level
    
    Current TTL: 300 seconds (5 mins)
    """

    def __init__(self, ttl_seconds: int = 300, max_size: int = 128):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._store: Dict[Any, Tuple[Any, float]] = {}

    def get(self, key: Any) -> Optional[Any]:
        now = time.time()
        if key not in self._store:
            return None
        value, ts = self._store[key]
        if now - ts > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: Any, value: Any) -> None:
        # Drop oldest item if at capacity to keep memory bounded
        if len(self._store) >= self.max_size:
            oldest_key = next(iter(self._store))
            self._store.pop(oldest_key, None)
        self._store[key] = (value, time.time())


class NominatimClient:
    """Lightweight client for OpenStreetMap's Nominatim service."""

    BASE_URL = "https://nominatim.openstreetmap.org"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, cache: Optional[SimpleTTLCache] = None):
        self.timeout = timeout
        self.cache = cache or SimpleTTLCache(ttl_seconds=300, max_size=256)
        self.headers = {"User-Agent": "TunisianTaxSystem/1.0"}

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.get(f"{self.BASE_URL}{path}", params=params, headers=self.headers, timeout=self.timeout)
        if response.status_code != 200:
            raise ExternalAPIError("Nominatim", response.status_code, f"Unexpected status {response.status_code}")
        return response.json()

    def geocode(self, query: str, limit: int = 1) -> Dict[str, Any]:
        cache_key = ("geocode", query, limit)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"q": query, "format": "json", "limit": limit}
        payload = self._request("/search", params)
        result = {
            "query": query,
            "results": [
                {
                    "lat": float(item.get("lat")),
                    "lon": float(item.get("lon")),
                    "display_name": item.get("display_name"),
                    "type": item.get("type"),
                    "category": item.get("class"),
                    "boundingbox": item.get("boundingbox"),
                }
                for item in payload or []
            ],
        }
        self.cache.set(cache_key, result)
        return result

    def reverse(self, latitude: float, longitude: float) -> Dict[str, Any]:
        cache_key = ("reverse", latitude, longitude)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"lat": latitude, "lon": longitude, "format": "json"}
        payload = self._request("/reverse", params)
        result = {
            "lat": latitude,
            "lon": longitude,
            "display_name": payload.get("display_name"),
            "address": payload.get("address", {}),
            "place_id": payload.get("place_id"),
            "type": payload.get("type"),
            "category": payload.get("class"),
        }
        self.cache.set(cache_key, result)
        return result


class NasaClient:
    """Client for NASA imagery search and Earth events."""

    IMAGES_URL = "https://images-api.nasa.gov/search"
    EONET_URL = "https://eonet.gsfc.nasa.gov/api/v2.1/events"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, cache: Optional[SimpleTTLCache] = None):
        self.timeout = timeout
        self.cache = cache or SimpleTTLCache(ttl_seconds=300, max_size=128)

    def search_imagery(self, query: str, media_type: str = "image", page: int = 1, page_size: int = 5) -> Dict[str, Any]:
        cache_key = ("images", query, media_type, page, page_size)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"q": query, "media_type": media_type, "page": page, "page_size": page_size}
        response = requests.get(self.IMAGES_URL, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise ExternalAPIError("NASA Images", response.status_code, f"Unexpected status {response.status_code}")

        payload = response.json() or {}
        collection = payload.get("collection", {})
        items = collection.get("items", [])
        parsed_items = []
        for item in items:
            data = (item.get("data") or [{}])[0]
            links = item.get("links") or []
            parsed_items.append(
                {
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "center": data.get("center"),
                    "date_created": data.get("date_created"),
                    "keywords": data.get("keywords", []),
                    "media_type": data.get("media_type"),
                    "href": links[0].get("href") if links else None,
                }
            )

        result = {
            "query": query,
            "media_type": media_type,
            "total": (collection.get("metadata") or {}).get("total_hits"),
            "items": parsed_items,
        }
        self.cache.set(cache_key, result)
        return result

    def list_events(self, limit: int = 5) -> Dict[str, Any]:
        cache_key = ("events", limit)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"limit": limit}
        response = requests.get(self.EONET_URL, params=params, timeout=self.timeout)
        if response.status_code != 200:
            raise ExternalAPIError("NASA EONET", response.status_code, f"Unexpected status {response.status_code}")

        payload = response.json() or {}
        events = payload.get("events", [])
        parsed_events = []
        for event in events:
            geometry = event.get("geometry") or []
            parsed_events.append(
                {
                    "title": event.get("title"),
                    "id": event.get("id"),
                    "categories": [c.get("title") for c in event.get("categories", []) if c.get("title")],
                    "updated": event.get("updated"),
                    "geometry": geometry[0] if geometry else None,
                }
            )

        result = {"events": parsed_events, "count": len(parsed_events)}
        self.cache.set(cache_key, result)
        return result
