"""EWPE Smart integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_DEVICE_KEY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDevice, EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EWPE Smart from a config entry."""
    host = entry.data[CONF_HOST]
    mac = entry.data[CONF_MAC]
    name = entry.data.get(CONF_NAME, "Ergo Air Purifier")
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    device_key = entry.data.get(CONF_DEVICE_KEY)
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)

    device = EWPEDevice(host=host, mac=mac, name=name, port=port, device_key=device_key)

    # Perform initial data fetch to validate connectivity
    try:
        await device.async_get_properties()
    except EWPEDeviceError as exc:
        raise ConfigEntryNotReady(f"Unable to connect to {host}: {exc}") from exc

    coordinator = EWPESmartCoordinator(hass, device, update_interval=update_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
