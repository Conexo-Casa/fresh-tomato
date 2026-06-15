"""DataUpdateCoordinator for FreshTomato."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FreshTomatoApi, FreshTomatoApiError, RouterStats
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FreshTomatoCoordinator(DataUpdateCoordinator[RouterStats]):
    """Coordinator that fetches all router data once per scan interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: FreshTomatoApi,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> RouterStats:
        try:
            return await self.api.async_get_stats()
        except FreshTomatoApiError as err:
            raise UpdateFailed(f"Error fetching FreshTomato data: {err}") from err
