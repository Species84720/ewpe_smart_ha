"""EWPE Smart device communication handler."""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import socket
from typing import Any

from Crypto.Cipher import AES

from .const import (
    DEFAULT_PORT,
    GENERIC_KEY,
    SOCKET_TIMEOUT,
    ALL_PARAMS,
    PARAM_PM25_A,
    PARAM_PM25_B,
    PARAM_POWER,
    PARAM_FAN_SPEED,
    PARAM_MODE,
    POWER_ON,
    POWER_OFF,
)

_LOGGER = logging.getLogger(__name__)


class EWPEDeviceError(Exception):
    """Raised when device communication fails."""


# ── AES helpers ──────────────────────────────────────────────────────────────

def _pad(s: str) -> str:
    n = 16 - len(s) % 16
    return s + chr(n) * n


def _unpad(b: bytes) -> bytes:
    return b[: -b[-1]]


def _encrypt(plaintext: str, key: str) -> str:
    cipher = AES.new(key.encode(), AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(_pad(plaintext).encode())).decode()


def _decrypt(ciphertext: str, key: str) -> dict:
    cipher = AES.new(key.encode(), AES.MODE_ECB)
    raw = _unpad(cipher.decrypt(base64.b64decode(ciphertext)))
    return json.loads(raw.decode())


# ── Packet builders ──────────────────────────────────────────────────────────

def _pack_request(tcid: str, pack: dict, key: str, i: int = 0) -> bytes:
    msg = {
        "cid": "app", "i": i, "t": "pack",
        "uid": 0, "tcid": tcid,
        "pack": _encrypt(json.dumps(pack), key),
    }
    return json.dumps(msg).encode()


def _scan_request() -> bytes:
    return json.dumps({"cid": "app", "i": 0, "t": "scan", "uid": 0, "tcid": ""}).encode()


# ── Device class ─────────────────────────────────────────────────────────────

class EWPEDevice:
    """Communicates with an EWPE Smart device over UDP."""

    def __init__(
        self,
        host: str,
        mac: str,
        name: str,
        port: int = DEFAULT_PORT,
        device_key: str | None = None,
    ) -> None:
        self.host = host
        self.mac = mac
        self.name = name
        self.port = port
        self.device_key: str = device_key or GENERIC_KEY
        self._properties: dict[str, Any] = {}
        # Track which PM25 key the device actually uses
        self._pm25_key: str | None = None

    @property
    def properties(self) -> dict[str, Any]:
        return self._properties

    # ── Low-level UDP ────────────────────────────────────────────────────────

    def _send_udp(self, payload: bytes) -> dict:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(SOCKET_TIMEOUT)
            s.sendto(payload, (self.host, self.port))
            data, _ = s.recvfrom(65535)
        return json.loads(data.decode())

    async def _async_send(self, payload: bytes) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_udp, payload)

    def _decrypt_response(self, response: dict) -> dict:
        return _decrypt(response["pack"], self.device_key)

    # ── Bind ─────────────────────────────────────────────────────────────────

    async def async_bind(self) -> str:
        """Perform bind handshake; returns device-specific encryption key."""
        pack = {"mac": self.mac, "t": "bind", "uid": 0}
        req = _pack_request(self.mac, pack, GENERIC_KEY, i=1)
        try:
            resp = await self._async_send(req)
            data = _decrypt(resp["pack"], GENERIC_KEY)
        except Exception as exc:
            raise EWPEDeviceError(f"Bind failed for {self.host}: {exc}") from exc

        key = data.get("key")
        if not key:
            raise EWPEDeviceError("Bind response missing key")
        self.device_key = key
        _LOGGER.debug("Bound %s → key=%s", self.host, key)
        return key

    # ── Poll ─────────────────────────────────────────────────────────────────

    async def async_get_properties(self, params: list[str] | None = None) -> dict[str, Any]:
        """Fetch current property values; auto-detects PM2.5 parameter key."""
        cols = params if params is not None else ALL_PARAMS
        pack = {"mac": self.mac, "t": "status", "cols": cols}
        req = _pack_request(self.mac, pack, self.device_key)
        try:
            resp = await self._async_send(req)
            data = self._decrypt_response(resp)
        except Exception as exc:
            raise EWPEDeviceError(f"Get properties failed for {self.host}: {exc}") from exc

        result: dict[str, Any] = dict(zip(data.get("cols", []), data.get("dat", [])))

        # Normalise PM2.5: whichever key has a non-None value wins;
        # expose it as the canonical PARAM_PM25_A so sensors always find it.
        if self._pm25_key is None:
            for k in (PARAM_PM25_A, PARAM_PM25_B):
                if result.get(k) is not None:
                    self._pm25_key = k
                    break

        if self._pm25_key and self._pm25_key != PARAM_PM25_A:
            result[PARAM_PM25_A] = result.pop(self._pm25_key, None)

        self._properties = result
        _LOGGER.debug("Properties %s: %s", self.host, result)
        return result

    # ── Command ──────────────────────────────────────────────────────────────

    async def async_set_properties(self, props: dict[str, Any]) -> bool:
        """Set one or more parameters on the device."""
        pack = {"opt": list(props.keys()), "p": list(props.values()), "t": "cmd"}
        req = _pack_request(self.mac, pack, self.device_key)
        try:
            resp = await self._async_send(req)
            data = self._decrypt_response(resp)
        except Exception as exc:
            raise EWPEDeviceError(f"Set properties failed for {self.host}: {exc}") from exc

        ok = data.get("r", -1) == 200
        if ok:
            self._properties.update(props)
        return ok

    # ── Convenience wrappers ─────────────────────────────────────────────────

    async def async_turn_on(self)  -> bool: return await self.async_set_properties({PARAM_POWER: POWER_ON})
    async def async_turn_off(self) -> bool: return await self.async_set_properties({PARAM_POWER: POWER_OFF})
    async def async_set_fan_speed(self, speed: int) -> bool: return await self.async_set_properties({PARAM_FAN_SPEED: speed})
    async def async_set_mode(self, mode: int)       -> bool: return await self.async_set_properties({PARAM_MODE: mode})

    # ── Discovery ────────────────────────────────────────────────────────────

    @staticmethod
    def scan_network(
        broadcast: str = "255.255.255.255",
        port: int = DEFAULT_PORT,
        timeout: float = 5.0,
    ) -> list[dict]:
        """Broadcast a scan and collect device responses."""
        found: list[dict] = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(timeout)
            s.sendto(_scan_request(), (broadcast, port))
            try:
                while True:
                    data, addr = s.recvfrom(65535)
                    try:
                        resp = json.loads(data.decode())
                        info = _decrypt(resp.get("pack", ""), GENERIC_KEY)
                        info["ip"] = addr[0]
                        found.append(info)
                    except Exception:
                        pass
            except socket.timeout:
                pass
        return found
