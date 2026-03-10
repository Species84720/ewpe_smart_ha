"""Sensor platform for EWPE Smart (Ergo Air Purifier)."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    AIR_QUALITY_MAP, CONF_HOST, CONF_MAC, CONF_NAME, DOMAIN,
    PARAM_PM25_A, PARAM_FILTER, PARAM_AIR_QUALITY,
)
from .coordinator import EWPESmartCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EWPESensorDesc(SensorEntityDescription):
    """Sensor description with EWPE extras."""
    param_key: str = ""
    value_map: dict | None = None


SENSOR_DESCRIPTIONS: tuple[EWPESensorDesc, ...] = (
    EWPESensorDesc(
        key="pm25",
        name="PM2.5",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        param_key=PARAM_PM25_A,   # coordinator normalises both variants to PARAM_PM25_A
        icon="mdi:air-filter",
    ),
    EWPESensorDesc(
        key="filter_allowance",
        name="Filter Allowance",   # matches the EWPE Smart app label
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        param_key=PARAM_FILTER,
        icon="mdi:air-filter",
    ),
    EWPESensorDesc(
        key="air_quality",
        name="Air Quality",
        param_key=PARAM_AIR_QUALITY,
        icon="mdi:weather-windy",
        value_map=AIR_QUALITY_MAP,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [EWPESmartSensor(coordinator, entry, desc) for desc in SENSOR_DESCRIPTIONS],
        update_before_add=True,
    )


class EWPESmartSensor(CoordinatorEntity[EWPESmartCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: EWPESensorDesc

    def __init__(self, coordinator: EWPESmartCoordinator, entry: ConfigEntry, desc: EWPESensorDesc) -> None:
        super().__init__(coordinator)
        self.entity_description = desc
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{desc.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def _data(self) -> dict: return self.coordinator.data or {}

    @property
    def native_value(self) -> Any:
        raw = self._data.get(self.entity_description.param_key)
        if raw is None:
            return None
        vm = self.entity_description.value_map
        return vm.get(int(raw), raw) if vm else raw

    @property
    def available(self) -> bool:
        return super().available and self.entity_description.param_key in self._data
