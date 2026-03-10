"""DataUpdateCoordinator for EWPE Smart."""
from __future__ import annotations
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .ewpe_device import EWPEDevice, EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


class EWPESmartCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, device: EWPEDevice, update_interval: int = SCAN_INTERVAL_SECONDS) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{device.mac}",
            update_interval=timedelta(seconds=update_interval),
        )
        self.device = device

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.device.async_get_properties()
        except EWPEDeviceError as exc:
            raise UpdateFailed(f"Error communicating with {self.device.host}: {exc}") from exc
