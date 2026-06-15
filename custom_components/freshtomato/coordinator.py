"""DataUpdateCoordinator for FreshTomato."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FreshTomatoApiError, FreshTomatoClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FreshTomatoCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that fetches all data from a FreshTomato router."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: FreshTomatoClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the router."""
        try:
            return await self.client.async_fetch_all()
        except FreshTomatoApiError as exc:
            raise UpdateFailed(f"FreshTomato update failed: {exc}") from exc
