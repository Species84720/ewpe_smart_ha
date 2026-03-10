"""Config flow for EWPE Smart integration."""
from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_KEY,
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PORT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .ewpe_device import EWPEDevice, EWPEDeviceError

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
    }
)


class EWPESmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EWPE Smart."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise flow."""
        self._host: str = ""
        self._port: int = DEFAULT_PORT
        self._name: str = DEFAULT_NAME
        self._mac: str = ""
        self._device_key: str = ""
        self._discovered_devices: list[dict] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step — optionally discover or enter manually."""
        errors: dict[str, str] = {}

        # Attempt auto-discovery first (non-blocking)
        if user_input is None:
            discovered = await self.hass.async_add_executor_job(
                EWPEDevice.scan_network
            )
            if discovered:
                self._discovered_devices = discovered
                return await self.async_step_select_device()

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, DEFAULT_PORT)
            self._name = user_input.get(CONF_NAME, DEFAULT_NAME)

            try:
                mac, key = await self._bind_device(self._host, self._port)
                self._mac = mac
                self._device_key = key
            except EWPEDeviceError as exc:
                _LOGGER.error("Failed to bind device at %s: %s", self._host, exc)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error connecting to %s", self._host)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(self._mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_MAC: self._mac,
                        CONF_NAME: self._name,
                        CONF_DEVICE_KEY: self._device_key,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={"port": str(DEFAULT_PORT)},
        )

    async def async_step_select_device(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Let the user pick a discovered device."""
        errors: dict[str, str] = {}

        device_options = {
            f"{d.get('ip')}|{d.get('mac', '')}": f"{d.get('name', 'Unknown')} ({d.get('ip')})"
            for d in self._discovered_devices
        }
        device_options["manual"] = "Enter IP address manually"

        if user_input is not None:
            selection = user_input.get("device")
            if selection == "manual":
                return await self.async_step_user()

            ip, mac = selection.split("|", 1)
            self._host = ip
            self._mac = mac
            device_info = next(
                (d for d in self._discovered_devices if d.get("ip") == ip), {}
            )
            self._name = device_info.get("name", DEFAULT_NAME)

            try:
                _, key = await self._bind_device(self._host, self._port, known_mac=self._mac)
                self._device_key = key
            except EWPEDeviceError as exc:
                _LOGGER.error("Bind failed: %s", exc)
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(self._mac)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=self._name,
                    data={
                        CONF_HOST: self._host,
                        CONF_PORT: self._port,
                        CONF_MAC: self._mac,
                        CONF_NAME: self._name,
                        CONF_DEVICE_KEY: self._device_key,
                    },
                )

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required("device"): vol.In(device_options)}
            ),
            errors=errors,
        )

    async def _bind_device(self, host: str, port: int, known_mac: str | None = None) -> tuple[str, str]:
        """Connect to device, retrieve MAC, and perform bind."""
        # If we don't have the MAC yet, do a directed scan
        if not known_mac:
            devices = await self.hass.async_add_executor_job(
                lambda: EWPEDevice.scan_network(broadcast=host, port=port, timeout=5.0)
            )
            if not devices:
                raise EWPEDeviceError(f"No EWPE device responded at {host}")
            known_mac = devices[0].get("mac", "")

        device = EWPEDevice(host=host, mac=known_mac, name="", port=port)
        key = await device.async_bind()
        return known_mac, key

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> EWPESmartOptionsFlow:
        """Return the options flow."""
        return EWPESmartOptionsFlow(config_entry)


class EWPESmartOptionsFlow(config_entries.OptionsFlow):
    """Handle EWPE Smart options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialise options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_UPDATE_INTERVAL, default=current_interval): vol.All(
                        int, vol.Range(min=10, max=300)
                    )
                }
            ),
        )
