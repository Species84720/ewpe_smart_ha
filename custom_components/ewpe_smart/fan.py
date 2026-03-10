"""Fan platform for EWPE Smart (Ergo Air Purifier)."""
from __future__ import annotations
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOST, CONF_MAC, CONF_NAME, DOMAIN,
    FAN_SPEED_AUTO, FAN_SPEED_HIGH, FAN_SPEED_LOW, FAN_SPEED_MEDIUM,
    FAN_SPEED_TO_PCT, NAME_TO_FAN_SPEED,
    MODE_AUTO, MODE_MANUAL, MODE_SLEEP,
    PARAM_FAN_SPEED, PARAM_MODE, PARAM_POWER,
    POWER_OFF, POWER_ON,
)
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDeviceError

_LOGGER = logging.getLogger(__name__)

PRESET_AUTO   = "Auto"
PRESET_MANUAL = "Manual"
PRESET_SLEEP  = "Sleep"

_MODE_TO_PRESET  = {MODE_AUTO: PRESET_AUTO, MODE_MANUAL: PRESET_MANUAL, MODE_SLEEP: PRESET_SLEEP}
_PRESET_TO_MODE  = {v: k for k, v in _MODE_TO_PRESET.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EWPESmartFan(coordinator, entry)], update_before_add=True)


class EWPESmartFan(CoordinatorEntity[EWPESmartCoordinator], FanEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = [PRESET_AUTO, PRESET_MANUAL, PRESET_SLEEP]

    def __init__(self, coordinator: EWPESmartCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._device = coordinator.device
        self._attr_unique_id = f"{entry.data[CONF_MAC]}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_MAC])},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def _d(self) -> dict: return self.coordinator.data or {}

    @property
    def is_on(self) -> bool | None:
        v = self._d.get(PARAM_POWER)
        return None if v is None else int(v) == POWER_ON

    @property
    def percentage(self) -> int | None:
        v = self._d.get(PARAM_FAN_SPEED)
        return None if v is None else FAN_SPEED_TO_PCT.get(int(v), 0)

    @property
    def speed_count(self) -> int: return 3

    @property
    def preset_mode(self) -> str | None:
        v = self._d.get(PARAM_MODE)
        return None if v is None else _MODE_TO_PRESET.get(int(v), PRESET_MANUAL)

    async def async_turn_on(self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any) -> None:
        props: dict[str, Any] = {PARAM_POWER: POWER_ON}
        if percentage is not None:
            props[PARAM_FAN_SPEED] = self._pct_to_speed(percentage)
        if preset_mode is not None:
            props[PARAM_MODE] = _PRESET_TO_MODE.get(preset_mode, MODE_MANUAL)
        try:
            await self._device.async_set_properties(props)
        except EWPEDeviceError as exc:
            _LOGGER.error("turn_on failed: %s", exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self._device.async_set_properties({PARAM_POWER: POWER_OFF})
        except EWPEDeviceError as exc:
            _LOGGER.error("turn_off failed: %s", exc)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        try:
            await self._device.async_set_properties(
                {PARAM_FAN_SPEED: self._pct_to_speed(percentage), PARAM_POWER: POWER_ON}
            )
        except EWPEDeviceError as exc:
            _LOGGER.error("set_percentage failed: %s", exc)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = _PRESET_TO_MODE.get(preset_mode)
        if mode is None:
            return
        try:
            await self._device.async_set_properties({PARAM_MODE: mode, PARAM_POWER: POWER_ON})
        except EWPEDeviceError as exc:
            _LOGGER.error("set_preset_mode failed: %s", exc)
        await self.coordinator.async_request_refresh()

    @staticmethod
    def _pct_to_speed(pct: int) -> int:
        if pct == 0: return FAN_SPEED_AUTO
        if pct <= 33: return FAN_SPEED_LOW
        if pct <= 66: return FAN_SPEED_MEDIUM
        return FAN_SPEED_HIGH
