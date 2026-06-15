# FreshTomato Router – Home Assistant Integration

[![HACS Custom Repository](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub Release](https://img.shields.io/github/release/Conexo-Casa/fresh-tomato.svg)](https://github.com/Conexo-Casa/fresh-tomato/releases)

A HACS-compatible Home Assistant integration for routers running [FreshTomato](https://freshtomato.org/) firmware (tested on the **Netgear R7000**; should work on any Broadcom-based router running FreshTomato 2020.8+).

---

## Features

| Category | What you get |
|---|---|
| **Status sensors** | WAN IP, Uptime, CPU load, Free/Total memory, Firmware version |
| **Network sensors** | Per-interface RX and TX byte counters (vlan1, eth0, br0, …) |
| **Wireless clients** | Count of connected Wi-Fi devices |
| **Device tracking** | One `device_tracker` entity per connected wireless client |

---

## Prerequisites

1. A router running **FreshTomato** firmware (Broadcom chipset).
2. Your router's **admin username and password**.
3. The router's **HTTP ID** — a session token used by the Tomato web UI.

### Finding your HTTP ID

1. Log in to your router's admin page (e.g. `http://192.168.1.1`).
2. Open any page (e.g. the Overview/Status page).
3. In your browser, view the page source (`Ctrl+U` / `Cmd+U`).
4. Search (`Ctrl+F`) for `http_id`.
5. Copy the value — it looks like `TomXXXXXXXX` or an 8-character alphanumeric string.

---

## Installation via HACS

1. In Home Assistant, go to **HACS → Integrations**.
2. Click the three-dot menu (⋮) → **Custom repositories**.
3. Add `https://github.com/Conexo-Casa/fresh-tomato` with category **Integration**.
4. Search for **FreshTomato Router** and click **Download**.
5. Restart Home Assistant.

## Manual Installation

1. Copy the `custom_components/freshtomato` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **FreshTomato Router**.
3. Fill in the form:

| Field | Description | Default |
|---|---|---|
| Router IP / Hostname | LAN IP of your router | — |
| HTTP Port | Web UI port | `80` |
| Admin Username | Router admin username | `admin` |
| Admin Password | Router admin password | — |
| HTTP ID | Session token (see above) | — |
| Verify SSL | Enable only if you have a valid cert | `false` |

### Options

After setup you can change the **poll interval** (10–3600 seconds, default 30 s) via **Settings → Devices & Services → FreshTomato Router → Configure**.

---

## Entities Created

### Sensors

| Entity | Description | Unit |
|---|---|---|
| `sensor.freshtomato_wan_ip_address` | Current WAN IP | — |
| `sensor.freshtomato_uptime` | Router uptime | s |
| `sensor.freshtomato_cpu_load_1_min` | 1-minute CPU load average | % |
| `sensor.freshtomato_free_memory` | Free RAM | B |
| `sensor.freshtomato_total_memory` | Total RAM | B |
| `sensor.freshtomato_firmware_version` | Installed firmware version | — |
| `sensor.freshtomato_wireless_clients` | Connected wireless clients | — |
| `sensor.freshtomato_<iface>_rx_bytes` | Bytes received on interface | B |
| `sensor.freshtomato_<iface>_tx_bytes` | Bytes sent on interface | B |

### Device Trackers

One `device_tracker.<mac_address>` entity per wireless client.
Note: the Tomato HTTP API only exposes **wireless** clients. Wired-only devices are not tracked (same limitation as the built-in HA Tomato integration).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Cannot connect" during setup | Check the router IP and port; ensure the router's web UI is reachable from the HA host |
| "Invalid auth" during setup | Double-check username, password, and HTTP ID |
| Sensors show `unknown` | The router may not expose all status fields; check HA logs for parse warnings |
| No wireless clients tracked | Confirm Wi-Fi is active and `wldev` endpoint returns data (try `http://<router>/update.cgi?exec=wldev&_http_id=<id>` in a browser) |

---

## About Conexo-Casa

[Conexo-Casa](https://github.com/Conexo-Casa) is a 501(c)(3) non-profit building accessible home-automation tools for people with neurocognitive impairments and the elderly.

## License

MIT — see [LICENSE](LICENSE).
