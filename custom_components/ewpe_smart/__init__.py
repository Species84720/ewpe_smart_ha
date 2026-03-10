"""EWPE Smart integration."""
from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_HOST, CONF_MAC, CONF_NAME, CONF_PORT, CONF_DEVICE_KEY,
    CONF_UPDATE_INTERVAL, DEFAULT_PORT, DEFAULT_UPDATE_INTERVAL, DOMAIN, PLATFORMS,
)
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDevice, EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    device = EWPEDevice(
        host=entry.data[CONF_HOST],
        mac=entry.data[CONF_MAC],
        name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
        port=entry.data.get(CONF_PORT, DEFAULT_PORT),
        device_key=entry.data.get(CONF_DEVICE_KEY),
    )
    try:
        await device.async_get_properties()
    except EWPEDeviceError as exc:
        raise ConfigEntryNotReady(f"Cannot connect to {entry.data[CONF_HOST]}: {exc}") from exc

    coordinator = EWPESmartCoordinator(
        hass, device,
        update_interval=entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(
        lambda h, e: h.config_entries.async_reload(e.entry_id)
    ))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
