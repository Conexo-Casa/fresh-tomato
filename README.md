# FreshTomato Router — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/conexo-casa/fresh-tomato.svg)](https://github.com/conexo-casa/fresh-tomato/releases)

A [HACS](https://hacs.xyz)-compatible Home Assistant custom integration for routers running [FreshTomato](https://freshtomato.org/) firmware (also compatible with other Tomato-based firmware such as Shibby, AdvancedTomato).

Tested on **Netgear R7000** running FreshTomato 2026.x.

---

## Features

| Entity type | What it tracks |
|---|---|
| **Sensors** | WAN download/upload bytes, LAN RX/TX, WiFi 2.4 GHz RX/TX, WiFi 5 GHz RX/TX, system uptime, load averages (1 / 5 / 15 min), memory total / free / used, connected device count |
| **Device Trackers** | Every device currently shown in the router's device list (MAC, IP, hostname, interface) |

---

## Prerequisites

1. FreshTomato (or Tomato/Shibby/AdvancedTomato) running on a Broadcom-based router.
2. HTTP access to the router's admin interface from your Home Assistant host.
3. Your **HTTP ID** — the internal token used by the Tomato web UI.

### Finding your HTTP ID

**Option A — Router web UI:**  
Administration → Admin Access → HTTP ID

**Option B — SSH / Telnet:**
```bash
nvram get http_id
```
The value looks like `TID16e6c81d29d9b44d`.

---

## Installation via HACS

1. Open HACS → **Integrations** → three-dot menu → **Custom repositories**.
2. Add `https://github.com/conexo-casa/fresh-tomato` with category **Integration**.
3. Click **Download** on the FreshTomato Router card.
4. Restart Home Assistant.

---

## Manual Installation

```bash
cp -r custom_components/freshtomato \
      <config_dir>/custom_components/freshtomato
```
Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **FreshTomato**.
3. Fill in the form:

| Field | Description |
|---|---|
| **Router IP / Hostname** | e.g. `192.168.1.1` |
| **HTTP Port** | Default `80`; use `443` with HTTPS |
| **Username** | Router admin username (usually `admin` or `root`) |
| **Password** | Router admin password |
| **HTTP ID** | See above — looks like `TID16e6c81d29d9b44d` |
| **Use HTTPS** | Enable if your router uses HTTPS |
| **Verify SSL** | Disable if using a self-signed certificate |
| **Polling interval** | Seconds between polls (default 30) |

---

## Sensor Reference

All sensors belong to the **FreshTomato Router** device.

| Sensor | Unit | Notes |
|---|---|---|
| WAN Download | bytes | Cumulative counter on `vlan2` |
| WAN Upload | bytes | Cumulative counter on `vlan2` |
| LAN RX / TX | bytes | Bridge `br0` |
| WiFi 2.4 GHz RX / TX | bytes | Interface `eth1` |
| WiFi 5 GHz RX / TX | bytes | Interface `eth2` (R7000) |
| Uptime | seconds | Use HA template to convert to days/hours |
| Load Average 1m / 5m / 15m | — | Linux-style load averages |
| Memory Total / Free / Used | kB | |
| Connected Devices | devices | Count of active DHCP/ARP entries |

> **Note on interface names:** Interface names (`vlan2`, `eth1`, `eth2`, etc.) vary by router model and firmware build. If WAN or WiFi sensors show `unavailable`, check your router's Status → Overview page and open a GitHub issue with your interface names.

---

## Device Tracker

Each device that appears in your router's device list gets a `device_tracker` entity. These update every polling cycle and can be used in presence-detection automations.

```yaml
# Example automation: notify when a device joins the network
automation:
  - alias: "Phone arrived home"
    trigger:
      - platform: state
        entity_id: device_tracker.my_phone
        to: "home"
    action:
      - service: notify.mobile_app
        data:
          message: "Welcome home!"
```

---

## Troubleshooting

**`cannot_connect`** — Verify the router IP is reachable from HA, and that port 80 (or 443) is not firewalled.

**`invalid_auth`** — Double-check username, password, and HTTP ID. The HTTP ID must exactly match the `http_id` nvram variable.

**Sensors stuck at `unavailable`** — The integration polls three separate CGI endpoints. If any one fails, only that group of sensors is affected. Check the HA logs for details.

**Interface names wrong** — The sensor definitions use common R7000 interface names. You can file an issue with your router model and interface names to get them added.

---

## Contributing

Issues and PRs welcome at [github.com/conexo-casa/fresh-tomato](https://github.com/conexo-casa/fresh-tomato).

---

## License

MIT License. See [LICENSE](LICENSE).
