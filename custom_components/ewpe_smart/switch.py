"""Switch platform for EWPE Smart — Child Lock."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_HOST, CONF_MAC, CONF_NAME, DOMAIN, PARAM_CHILD_LOCK
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ChildLockSwitch(coordinator, entry)], update_before_add=True)


class ChildLockSwitch(CoordinatorEntity[EWPESmartCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Child Lock"
    _attr_icon = "mdi:lock-outline"

    def __init__(self, coordinator: EWPESmartCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_child_lock"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def is_on(self) -> bool | None:
        v = (self.coordinator.data or {}).get(PARAM_CHILD_LOCK)
        return None if v is None else bool(int(v))

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.device.async_set_properties({PARAM_CHILD_LOCK: 1})
        except EWPEDeviceError as exc:
            _LOGGER.error("child_lock on failed: %s", exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.device.async_set_properties({PARAM_CHILD_LOCK: 0})
        except EWPEDeviceError as exc:
            _LOGGER.error("child_lock off failed: %s", exc)
        await self.coordinator.async_request_refresh()
