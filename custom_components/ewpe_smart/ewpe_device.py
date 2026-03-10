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
    PARAM_POWER,
    PARAM_FAN_SPEED,
    PARAM_MODE,
    PARAM_PM25,
    PARAM_FILTER_LIFE,
    PARAM_AIR_QUALITY,
    PARAM_CHILD_LOCK,
    PARAM_SLEEP,
    PARAM_LIGHT,
)

_LOGGER = logging.getLogger(__name__)

PACK_TYPE_GENERIC = "pack"
CMD_SCAN = "scan"
CMD_BIND = "bind"
CMD_GET = "status"
CMD_SET = "cmd"


class EWPEDeviceError(Exception):
    """Raised when a device communication error occurs."""


def _pad(s: str) -> str:
    """Pad string to AES block size."""
    block_size = 16
    return s + (block_size - len(s) % block_size) * chr(block_size - len(s) % block_size)


def _unpad(s: bytes) -> bytes:
    """Remove padding from decrypted bytes."""
    return s[: -s[-1]]


def _encrypt(plaintext: str, key: str) -> str:
    """Encrypt plaintext using AES-128 ECB."""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
    encrypted = cipher.encrypt(_pad(plaintext).encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def _decrypt(ciphertext: str, key: str) -> dict:
    """Decrypt base64 ciphertext using AES-128 ECB and return parsed JSON."""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_ECB)
    decrypted = _unpad(cipher.decrypt(base64.b64decode(ciphertext)))
    return json.loads(decrypted.decode("utf-8"))


def _create_request(tcid: str, pack_type: str, pack: dict, i: int = 0) -> bytes:
    """Build a UDP request packet."""
    msg = {
        "cid": "app",
        "i": i,
        "t": pack_type,
        "uid": 0,
        "tcid": tcid,
        "pack": pack,
    }
    return json.dumps(msg).encode("utf-8")


def _create_encrypted_request(tcid: str, pack: dict, key: str, i: int = 0) -> bytes:
    """Build an encrypted UDP request packet."""
    encrypted_pack = _encrypt(json.dumps(pack), key)
    msg = {
        "cid": "app",
        "i": i,
        "t": PACK_TYPE_GENERIC,
        "uid": 0,
        "tcid": tcid,
        "pack": encrypted_pack,
    }
    return json.dumps(msg).encode("utf-8")


class EWPEDevice:
    """Represents an EWPE Smart compatible device (Ergo Air Purifier)."""

    def __init__(
        self,
        host: str,
        mac: str,
        name: str,
        port: int = DEFAULT_PORT,
        device_key: str | None = None,
    ) -> None:
        """Initialise the device."""
        self.host = host
        self.mac = mac
        self.name = name
        self.port = port
        self.device_key = device_key or GENERIC_KEY
        self._properties: dict[str, Any] = {}

    @property
    def properties(self) -> dict[str, Any]:
        """Return the last fetched device properties."""
        return self._properties

    def _send_udp(self, payload: bytes, timeout: float = SOCKET_TIMEOUT) -> dict:
        """Send a UDP packet and return the parsed JSON response."""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(payload, (self.host, self.port))
            data, _ = sock.recvfrom(65535)
        return json.loads(data.decode("utf-8"))

    async def _async_send_udp(self, payload: bytes) -> dict:
        """Send UDP packet asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._send_udp, payload)

    async def async_bind(self) -> str:
        """Perform the bind handshake to get the device-specific key."""
        pack = {"mac": self.mac, "t": CMD_BIND, "uid": 0}
        request = _create_encrypted_request(self.mac, pack, GENERIC_KEY, i=1)
        try:
            response = await self._async_send_udp(request)
        except (OSError, socket.timeout) as exc:
            raise EWPEDeviceError(f"Bind failed for {self.host}: {exc}") from exc

        pack_data = response.get("pack", "")
        try:
            decrypted = _decrypt(pack_data, GENERIC_KEY)
        except Exception as exc:  # noqa: BLE001
            raise EWPEDeviceError(f"Failed to decrypt bind response: {exc}") from exc

        key = decrypted.get("key")
        if not key:
            raise EWPEDeviceError("Bind response did not contain a key")

        self.device_key = key
        _LOGGER.debug("Bound to %s, key=%s", self.host, key)
        return key

    async def async_get_properties(self, params: list[str] | None = None) -> dict[str, Any]:
        """Fetch the current property values from the device."""
        if params is None:
            params = [
                PARAM_POWER,
                PARAM_FAN_SPEED,
                PARAM_MODE,
                PARAM_PM25,
                PARAM_FILTER_LIFE,
                PARAM_AIR_QUALITY,
                PARAM_CHILD_LOCK,
                PARAM_SLEEP,
                PARAM_LIGHT,
            ]

        pack = {"mac": self.mac, "t": CMD_GET, "cols": params}
        request = _create_encrypted_request(self.mac, pack, self.device_key)

        try:
            response = await self._async_send_udp(request)
        except (OSError, socket.timeout) as exc:
            raise EWPEDeviceError(f"Get properties failed for {self.host}: {exc}") from exc

        pack_data = response.get("pack", "")
        try:
            decrypted = _decrypt(pack_data, self.device_key)
        except Exception as exc:  # noqa: BLE001
            raise EWPEDeviceError(f"Failed to decrypt status response: {exc}") from exc

        cols = decrypted.get("cols", [])
        dat = decrypted.get("dat", [])
        self._properties = dict(zip(cols, dat))
        _LOGGER.debug("Properties for %s: %s", self.host, self._properties)
        return self._properties

    async def async_set_properties(self, properties: dict[str, Any]) -> bool:
        """Set one or more property values on the device."""
        opt = list(properties.keys())
        p = list(properties.values())

        pack = {"opt": opt, "p": p, "t": CMD_SET}
        request = _create_encrypted_request(self.mac, pack, self.device_key)

        try:
            response = await self._async_send_udp(request)
        except (OSError, socket.timeout) as exc:
            raise EWPEDeviceError(f"Set properties failed for {self.host}: {exc}") from exc

        pack_data = response.get("pack", "")
        try:
            decrypted = _decrypt(pack_data, self.device_key)
        except Exception as exc:  # noqa: BLE001
            raise EWPEDeviceError(f"Failed to decrypt set response: {exc}") from exc

        result = decrypted.get("r", -1)
        success = result == 200
        if success:
            # Optimistically update local state
            self._properties.update(properties)
        return success

    # ---- Convenience helpers ------------------------------------------------

    async def async_turn_on(self) -> bool:
        """Turn the device on."""
        return await self.async_set_properties({PARAM_POWER: 1})

    async def async_turn_off(self) -> bool:
        """Turn the device off."""
        return await self.async_set_properties({PARAM_POWER: 0})

    async def async_set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (0=Auto, 1=Low, 2=Medium, 3=High)."""
        return await self.async_set_properties({PARAM_FAN_SPEED: speed})

    async def async_set_mode(self, mode: int) -> bool:
        """Set operating mode (0=Auto, 1=Manual, 2=Sleep)."""
        return await self.async_set_properties({PARAM_MODE: mode})

    # ---- Static helpers for discovery ---------------------------------------

    @staticmethod
    def scan_network(broadcast: str = "255.255.255.255", port: int = DEFAULT_PORT, timeout: float = 5.0) -> list[dict]:
        """Broadcast a scan packet and collect device responses."""
        scan_pack = {"t": CMD_SCAN}
        request = _create_request("", CMD_SCAN, scan_pack)

        found: list[dict] = []
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.sendto(request, (broadcast, port))

            try:
                while True:
                    data, addr = sock.recvfrom(65535)
                    try:
                        resp = json.loads(data.decode("utf-8"))
                        pack_data = resp.get("pack", "")
                        device_info = _decrypt(pack_data, GENERIC_KEY)
                        device_info["ip"] = addr[0]
                        found.append(device_info)
                        _LOGGER.debug("Discovered device: %s", device_info)
                    except Exception:  # noqa: BLE001
                        pass
            except socket.timeout:
                pass

        return found
