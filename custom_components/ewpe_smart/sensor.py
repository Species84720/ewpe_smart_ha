"""Sensor platform for EWPE Smart (Ergo Air Purifier)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    AIR_QUALITY_MAP,
    ATTR_AIR_QUALITY,
    ATTR_FILTER_LIFE,
    ATTR_PM25,
    CONF_MAC,
    CONF_NAME,
    CONF_HOST,
    DOMAIN,
    PARAM_AIR_QUALITY,
    PARAM_FILTER_LIFE,
    PARAM_PM25,
)
from .coordinator import EWPESmartCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EWPESensorEntityDescription(SensorEntityDescription):
    """Description of an EWPE Smart sensor."""

    param_key: str = ""
    value_map: dict | None = None


SENSOR_DESCRIPTIONS: tuple[EWPESensorEntityDescription, ...] = (
    EWPESensorEntityDescription(
        key=ATTR_PM25,
        name="PM2.5",
        device_class=SensorDeviceClass.PM25,
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        state_class=SensorStateClass.MEASUREMENT,
        param_key=PARAM_PM25,
        icon="mdi:air-filter",
    ),
    EWPESensorEntityDescription(
        key=ATTR_FILTER_LIFE,
        name="Filter Life Remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        param_key=PARAM_FILTER_LIFE,
        icon="mdi:air-filter",
    ),
    EWPESensorEntityDescription(
        key=ATTR_AIR_QUALITY,
        name="Air Quality",
        param_key=PARAM_AIR_QUALITY,
        icon="mdi:weather-windy",
        value_map=AIR_QUALITY_MAP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator: EWPESmartCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            EWPESmartSensor(coordinator, entry, description)
            for description in SENSOR_DESCRIPTIONS
        ],
        update_before_add=True,
    )


class EWPESmartSensor(CoordinatorEntity[EWPESmartCoordinator], SensorEntity):
    """Representation of an EWPE Smart sensor."""

    _attr_has_entity_name = True
    entity_description: EWPESensorEntityDescription

    def __init__(
        self,
        coordinator: EWPESmartCoordinator,
        entry: ConfigEntry,
        description: EWPESensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.data.get(CONF_NAME, "Ergo Air Purifier"),
            manufacturer="Ergo / EWPE Smart",
            model="Air Purifier",
            configuration_url=f"http://{entry.data[CONF_HOST]}",
        )

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        raw = self._data.get(self.entity_description.param_key)
        if raw is None:
            return None
        value_map = self.entity_description.value_map
        if value_map is not None:
            return value_map.get(int(raw), raw)
        return raw

    @property
    def available(self) -> bool:
        """Return True if coordinator data contains this sensor's key."""
        return (
            super().available
            and self.entity_description.param_key in self._data
        )
