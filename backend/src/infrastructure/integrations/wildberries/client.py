"""Wildberries integration adapter (httpx, async)."""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from application.interfaces import WbSyncResult
from config.settings import Settings

logger = logging.getLogger("checkstock.wildberries")

_CARDS_PATH = "/content/v2/get/cards/list"
_FBS_ORDERS_PATH = "/api/v3/orders/new"
_FBO_SUPPLIES_PATH = "/api/v3/supplies"


class WildberriesClient:
    """Adapter for Wildberries API.

    Internal CheckStock stocks remain the source of truth; this adapter only
    *reads* external data and never mutates physical stock.
    """

    def __init__(self, settings: Settings) -> None:
        self._token = settings.wb_api_token
        self._content_url = settings.wb_content_base_url.rstrip("/")
        self._marketplace_url = settings.wb_marketplace_base_url.rstrip("/")
        self._timeout = settings.wb_request_timeout
        self._max_retries = settings.wb_max_retries
        self._min_interval = 0.2  # naive rate limiting between requests
        self._last_request_at = 0.0

    def is_configured(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._token or "", "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        base: str,
        path: str,
        *,
        json_body: dict | None = None,
    ) -> dict:
        await self._throttle()
        url = f"{base}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            last_error: Exception | None = None
            for attempt in range(self._max_retries):
                try:
                    resp = await client.request(
                        method, url, headers=self._headers(), json=json_body
                    )
                    if resp.status_code == 401:
                        raise WildberriesAuthError("WB token is invalid or expired (401)")
                    if resp.status_code == 429:
                        retry_after = float(resp.headers.get("Retry-After", "1"))
                        await asyncio.sleep(retry_after)
                        raise WildberriesRateLimitError("WB rate limit hit (429)")
                    resp.raise_for_status()
                    return resp.json()
                except (httpx.HTTPError, WildberriesRateLimitError) as exc:
                    last_error = exc
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(2**attempt)
            assert last_error is not None
            raise WildberriesError(f"WB request failed: {last_error}")

    async def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_at = time.monotonic()

    async def sync_cards(self) -> list[dict]:
        """Fetch the product cards list (content API)."""
        body = {"settings": {"cursor": {"limit": 100}, "filter": {"withPhoto": -1}}}
        data = await self._request("POST", self._content_url, _CARDS_PATH, json_body=body)
        cards = data.get("cards", [])
        logger.info("synced %d WB cards", len(cards))
        return cards

    async def sync_fbs_orders(self) -> list[dict]:
        """Fetch new FBS orders (marketplace API)."""
        data = await self._request("GET", self._marketplace_url, _FBS_ORDERS_PATH)
        orders = data.get("orders", [])
        logger.info("synced %d WB FBS orders", len(orders))
        return orders

    async def sync_fbo_supplies(self) -> list[dict]:
        """Fetch the list of FBO supplies (marketplace API)."""
        data = await self._request("GET", self._marketplace_url, _FBO_SUPPLIES_PATH)
        supplies = data.get("supplies", [])
        logger.info("synced %d WB FBO supplies", len(supplies))
        return supplies

    async def sync(self) -> WbSyncResult:
        cards = await self.sync_cards()
        orders = await self.sync_fbs_orders()
        supplies = await self.sync_fbo_supplies()
        return WbSyncResult(
            demo_mode=False,
            cards_count=len(cards),
            fbs_orders_count=len(orders),
            external_stocks=[],
            raw={"cards": len(cards), "fbs_orders": len(orders), "fbo_supplies": len(supplies)},
        )


class WildberriesError(Exception):
    pass


class WildberriesAuthError(WildberriesError):
    pass


class WildberriesRateLimitError(WildberriesError):
    pass
