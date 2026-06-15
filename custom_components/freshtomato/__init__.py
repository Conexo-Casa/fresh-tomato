"""FreshTomato Router integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FreshTomatoApi
from .const import (
    CONF_HTTP_ID,
    CONF_SSL,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import FreshTomatoCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.DEVICE_TRACKER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FreshTomato from a config entry."""
    data = entry.data

    session = async_get_clientsession(hass, data.get(CONF_VERIFY_SSL, True))
    api = FreshTomatoApi(
        host=data[CONF_HOST],
        http_id=data[CONF_HTTP_ID],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        port=data.get(CONF_PORT, DEFAULT_PORT),
        ssl=data.get(CONF_SSL, False),
        verify_ssl=data.get(CONF_VERIFY_SSL, True),
        session=session,
    )

    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )

    coordinator = FreshTomatoCoordinator(hass, api, scan_interval=scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: FreshTomatoCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
