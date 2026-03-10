"""Select platform for EWPE Smart — Mode and Fan Speed dropdowns."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_HOST, CONF_MAC, CONF_NAME, DOMAIN,
    FAN_SPEED_TO_NAME, NAME_TO_FAN_SPEED, FAN_SPEED_NAMES,
    MODE_TO_NAME, NAME_TO_MODE, MODE_NAMES,
    PARAM_FAN_SPEED, PARAM_MODE,
)
from .coordinator import EWPESmartCoordinator
from .ewpe_device import EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EWPESelectDescription(SelectEntityDescription):
    param_key: str = ""
    val_to_name: dict = None  # type: ignore[assignment]
    name_to_val: dict = None  # type: ignore[assignment]


SELECT_DESCRIPTIONS: tuple[EWPESelectDescription, ...] = (
    EWPESelectDescription(
        key="mode",
        name="Mode",
        icon="mdi:cog-outline",
        options=MODE_NAMES,
        param_key=PARAM_MODE,
        val_to_name=MODE_TO_NAME,
        name_to_val=NAME_TO_MODE,
    ),
    EWPESelectDescription(
        key="fan_speed",
        name="Fan Speed",
        icon="mdi:fan",
        options=FAN_SPEED_NAMES,
        param_key=PARAM_FAN_SPEED,
        val_to_name=FAN_SPEED_TO_NAME,
        name_to_val=NAME_TO_FAN_SPEED,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [EWPESelect(coordinator, entry, desc) for desc in SELECT_DESCRIPTIONS],
        update_before_add=True,
    )


class EWPESelect(CoordinatorEntity[EWPESmartCoordinator], SelectEntity):
    _attr_has_entity_name = True
    entity_description: EWPESelectDescription

    def __init__(self, coordinator: EWPESmartCoordinator, entry: ConfigEntry, desc: EWPESelectDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{desc.key}"
        self._attr_options = desc.options
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def current_option(self) -> str | None:
        v = (self.coordinator.data or {}).get(self.entity_description.param_key)
        if v is None:
            return None
        return self.entity_description.val_to_name.get(int(v))

    async def async_select_option(self, option: str) -> None:
        val = self.entity_description.name_to_val.get(option)
        if val is None:
            _LOGGER.warning("Unknown option '%s' for %s", option, self.entity_description.key)
            return
        try:
            await self.coordinator.device.async_set_properties({self.entity_description.param_key: val})
        except EWPEDeviceError as exc:
            _LOGGER.error("select_option failed: %s", exc)
        await self.coordinator.async_request_refresh()
