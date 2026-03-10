"""Config flow for EWPE Smart."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_DEVICE_KEY, CONF_HOST, CONF_MAC, CONF_NAME, CONF_PORT,
    CONF_UPDATE_INTERVAL, DEFAULT_NAME, DEFAULT_PORT, DEFAULT_UPDATE_INTERVAL, DOMAIN,
)
from .ewpe_device import EWPEDevice, EWPEDeviceError

_LOGGER = logging.getLogger(__name__)


class EWPESmartConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._host = ""
        self._port = DEFAULT_PORT
        self._name = DEFAULT_NAME
        self._mac = ""
        self._key = ""
        self._discovered: list[dict] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is None:
            devices = await self.hass.async_add_executor_job(EWPEDevice.scan_network)
            if devices:
                self._discovered = devices
                return await self.async_step_select()

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input.get(CONF_PORT, DEFAULT_PORT)
            self._name = user_input.get(CONF_NAME, DEFAULT_NAME)
            try:
                self._mac, self._key = await self._do_bind(self._host, self._port)
            except EWPEDeviceError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(self._mac)
                self._abort_if_unique_id_configured()
                return self._create()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }),
            errors=errors,
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        options = {
            f"{d.get('ip')}||{d.get('mac','')}": f"{d.get('name','Unknown')} ({d.get('ip')})"
            for d in self._discovered
        }
        options["__manual__"] = "Enter IP manually…"

        if user_input is not None:
            sel = user_input["device"]
            if sel == "__manual__":
                return await self.async_step_user()
            ip, mac = sel.split("||", 1)
            self._host, self._mac = ip, mac
            self._name = next((d.get("name", DEFAULT_NAME) for d in self._discovered if d.get("ip") == ip), DEFAULT_NAME)
            try:
                _, self._key = await self._do_bind(self._host, self._port, known_mac=self._mac)
            except EWPEDeviceError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(self._mac)
                self._abort_if_unique_id_configured()
                return self._create()

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema({vol.Required("device"): vol.In(options)}),
            errors=errors,
        )

    def _create(self) -> FlowResult:
        return self.async_create_entry(
            title=self._name,
            data={
                CONF_HOST: self._host, CONF_PORT: self._port,
                CONF_MAC: self._mac, CONF_NAME: self._name,
                CONF_DEVICE_KEY: self._key,
            },
        )

    async def _do_bind(self, host: str, port: int, known_mac: str | None = None) -> tuple[str, str]:
        if not known_mac:
            devices = await self.hass.async_add_executor_job(
                lambda: EWPEDevice.scan_network(broadcast=host, port=port, timeout=5.0)
            )
            if not devices:
                raise EWPEDeviceError(f"No EWPE device at {host}")
            known_mac = devices[0].get("mac", "")
        dev = EWPEDevice(host=host, mac=known_mac, name="", port=port)
        key = await dev.async_bind()
        return known_mac, key

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry) -> "EWPEOptionsFlow":
        return EWPEOptionsFlow(entry)


class EWPEOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                ): vol.All(int, vol.Range(min=10, max=300)),
            }),
        )
