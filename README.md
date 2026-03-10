# EWPE Smart — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
![version](https://img.shields.io/badge/version-1.0.0-blue)

A Home Assistant custom integration for **EWPE Smart** compatible air purifiers, including **Ergo** branded devices.

---

## Features

- 🌀 **Fan entity** — power on/off, fan speed (Auto / Low / Medium / High), preset modes (Auto / Manual / Sleep)
- 📊 **Sensor entities** — PM2.5 concentration, filter life remaining (%), air quality index
- 🔍 **Auto-discovery** — automatically finds devices on your local network
- 🔒 **Encrypted communication** — uses the EWPE Smart AES protocol
- ⚙️ **Options flow** — configurable polling interval (10–300 seconds)

---

## Requirements

| Requirement | Details |
|---|---|
| Home Assistant | ≥ 2023.1 |
| Python package | `pycryptodome ≥ 3.15.0` (auto-installed) |
| Device setup | Device must be configured via the **EWPE Smart** or **Ergo Smart** app first |

---

## Installation

### Via HACS (recommended)

1. Open **HACS → Integrations**.
2. Click the **⋮** menu → **Custom repositories**.
3. Add `https://github.com/yourusername/ewpe-smart-ha` with category **Integration**.
4. Search for **EWPE Smart** and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/ewpe_smart/` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **EWPE Smart**.
3. The integration will attempt to auto-discover devices on your network.
4. Select your device from the list, or enter its IP address manually.
5. The integration will perform a key-exchange and begin polling.

> **Tip:** Assign a static IP to your purifier in your router's DHCP settings to prevent the IP from changing.

---

## Entities

### Fan — `fan.ergo_air_purifier`

| Feature | Description |
|---|---|
| On / Off | Power the device on or off |
| Speed | Auto (0%), Low (33%), Medium (66%), High (100%) |
| Preset modes | **Auto** — device controls speed automatically |
| | **Manual** — use the speed slider |
| | **Sleep** — quiet night mode |

**Attributes:**
- `child_lock` — whether child lock is enabled
- `sleep_mode` — whether sleep mode is active
- `light` — whether the display light is on

### Sensors

| Entity | Unit | Description |
|---|---|---|
| `sensor.ergo_air_purifier_pm2_5` | µg/m³ | Particulate matter (PM2.5) |
| `sensor.ergo_air_purifier_filter_life_remaining` | % | Filter life remaining |
| `sensor.ergo_air_purifier_air_quality` | — | Air quality: Excellent / Good / Moderate / Poor |

---

## Protocol Notes

EWPE Smart devices communicate over **UDP port 7000** using **AES-128 ECB** encrypted JSON packets. The integration:

1. Broadcasts a scan packet to discover devices.
2. Performs a bind handshake using the generic key to obtain the device-specific encryption key.
3. Polls the device every 30 seconds (configurable) using the device key.

---

## Troubleshooting

**Device not discovered automatically**
- Ensure your HA instance and the purifier are on the same subnet.
- Check that UDP port 7000 is not blocked by a firewall.
- Enter the IP address manually if auto-discovery fails.

**`cannot_connect` error**
- Verify the device is online and the EWPE Smart app can still reach it.
- Re-pair the device with the app if necessary, then retry adding the integration.

**Sensors show `unavailable`**
- Not all Ergo models expose PM2.5 or filter sensors. The fan entity will still work.

---

## Contributing

Pull requests are welcome! Please open an issue first for large changes.

## License

MIT License — see [LICENSE](LICENSE) for details.
