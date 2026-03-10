"""Fan platform for EWPE Smart (Ergo Air Purifier)."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    DOMAIN,
    FAN_SPEED_AUTO,
    FAN_SPEED_HIGH,
    FAN_SPEED_LOW,
    FAN_SPEED_MEDIUM,
    FAN_SPEED_NAMES,
    FAN_SPEED_TO_PCT,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_NAMES,
    MODE_SLEEP,
    PARAM_CHILD_LOCK,
    PARAM_FAN_SPEED,
    PARAM_LIGHT,
    PARAM_MODE,
    PARAM_POWER,
    PARAM_SLEEP,
    POWER_OFF,
    POWER_ON,
)
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDeviceError

_LOGGER = logging.getLogger(__name__)

PRESET_AUTO = "Auto"
PRESET_MANUAL = "Manual"
PRESET_SLEEP = "Sleep"

PRESET_MODES = [PRESET_AUTO, PRESET_MANUAL, PRESET_SLEEP]

_MODE_TO_PRESET = {
    MODE_AUTO: PRESET_AUTO,
    MODE_MANUAL: PRESET_MANUAL,
    MODE_SLEEP: PRESET_SLEEP,
}
_PRESET_TO_MODE = {v: k for k, v in _MODE_TO_PRESET.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the fan platform."""
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [EWPESmartFan(coordinator, entry)],
        update_before_add=True,
    )


class EWPESmartFan(CoordinatorEntity[EWPESmartCoordinator], FanEntity):
    """Representation of an EWPE Smart air purifier as a fan entity."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES

    def __init__(self, coordinator: EWPESmartCoordinator, entry: ConfigEntry) -> None:
        """Initialise the fan entity."""
        super().__init__(coordinator)
        self._device = coordinator.device
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_MAC]}_fan"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_MAC])},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    # ---- State properties --------------------------------------------------

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def is_on(self) -> bool | None:
        """Return True if the device is on."""
        power = self._data.get(PARAM_POWER)
        if power is None:
            return None
        return int(power) == POWER_ON

    @property
    def percentage(self) -> int | None:
        """Return current fan speed as a percentage."""
        speed = self._data.get(PARAM_FAN_SPEED)
        if speed is None:
            return None
        return FAN_SPEED_TO_PCT.get(int(speed), 0)

    @property
    def speed_count(self) -> int:
        """Return the number of discrete fan speeds."""
        return 3  # Low / Medium / High (Auto is handled via preset)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        mode = self._data.get(PARAM_MODE)
        if mode is None:
            return None
        return _MODE_TO_PRESET.get(int(mode), PRESET_MANUAL)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {}
        if (child_lock := self._data.get(PARAM_CHILD_LOCK)) is not None:
            attrs["child_lock"] = bool(int(child_lock))
        if (sleep := self._data.get(PARAM_SLEEP)) is not None:
            attrs["sleep_mode"] = bool(int(sleep))
        if (light := self._data.get(PARAM_LIGHT)) is not None:
            attrs["light"] = bool(int(light))
        return attrs

    # ---- Commands ----------------------------------------------------------

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        props: dict[str, Any] = {PARAM_POWER: POWER_ON}
        if percentage is not None:
            props[PARAM_FAN_SPEED] = self._pct_to_speed(percentage)
        if preset_mode is not None:
            props[PARAM_MODE] = _PRESET_TO_MODE.get(preset_mode, MODE_MANUAL)
        try:
            await self._device.async_set_properties(props)
        except EWPEDeviceError as exc:
            _LOGGER.error("Failed to turn on %s: %s", self._device.host, exc)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        try:
            await self._device.async_set_properties({PARAM_POWER: POWER_OFF})
        except EWPEDeviceError as exc:
            _LOGGER.error("Failed to turn off %s: %s", self._device.host, exc)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed from percentage."""
        speed = self._pct_to_speed(percentage)
        try:
            await self._device.async_set_properties({PARAM_FAN_SPEED: speed, PARAM_POWER: POWER_ON})
        except EWPEDeviceError as exc:
            _LOGGER.error("Failed to set speed on %s: %s", self._device.host, exc)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set operating mode (preset)."""
        mode = _PRESET_TO_MODE.get(preset_mode)
        if mode is None:
            _LOGGER.warning("Unknown preset mode: %s", preset_mode)
            return
        try:
            await self._device.async_set_properties({PARAM_MODE: mode, PARAM_POWER: POWER_ON})
        except EWPEDeviceError as exc:
            _LOGGER.error("Failed to set mode on %s: %s", self._device.host, exc)
        await self.coordinator.async_request_refresh()

    # ---- Helpers -----------------------------------------------------------

    @staticmethod
    def _pct_to_speed(percentage: int) -> int:
        """Convert percentage to discrete fan speed value."""
        if percentage == 0:
            return FAN_SPEED_AUTO
        if percentage <= 33:
            return FAN_SPEED_LOW
        if percentage <= 66:
            return FAN_SPEED_MEDIUM
        return FAN_SPEED_HIGH
