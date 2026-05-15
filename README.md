# Check Online

A [Home Assistant](https://www.home-assistant.io) custom integration that monitors your network connectivity by pinging configurable targets. It exposes a primary **Online** binary sensor along with per-target diagnostics, so you can build automations that react to network outages.

## Features

- Pings 3 configurable targets (IPs or hostnames) to determine connectivity
- Retry-based state transitions to avoid false positives from transient failures
- Faster polling interval while offline for quicker recovery detection
- Per-target status and round-trip time sensors for diagnostics
- Tracks when the network last went online/offline

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** > **Custom repositories**
3. Add this repository URL and select **Integration** as the category
4. Install **Check Online**
5. Restart Home Assistant

### Manual

Copy the `custom_components/check_online` directory into your Home Assistant `custom_components/` folder and restart.

## Configuration

Add the integration via **Settings > Devices & Services > Add Integration > Check Online**.

You'll be asked to provide 3 ping targets. The defaults are:

| Target   | Default   |
|----------|-----------|
| Target 1 | `8.8.8.8` |
| Target 2 | `1.1.1.1` |
| Target 3 | `9.9.9.9` |

### Options

All settings can be changed at any time via the integration's **Configure** button:

| Option | Default | Description |
|--------|---------|-------------|
| Scan interval (online) | 60s | How often to ping when the network is up |
| Scan interval (offline) | 30s | How often to ping when the network is down |
| Retry delay | 5s | Delay between retries when all pings fail |
| Retry count | 2 | Number of retries before declaring offline |
| Ping timeout | 500ms | Timeout for each individual ping |

### YAML configuration

```yaml
check_online:
  targets:
    - 8.8.8.8
    - 1.1.1.1
    - 9.9.9.9
  scan_interval: 60
  offline_interval: 30
  retry_delay: 5
  retry_count: 2
  ping_timeout: 500
```

## Entities

### Binary sensors

| Entity | Description |
|--------|-------------|
| Online | `on` when any target responds, `off` when all targets fail after retries |
| Target 1/2/3 status | Individual target reachability (diagnostic) |

### Sensors

| Entity | Description |
|--------|-------------|
| Target 1/2/3 RTT | Round-trip time in milliseconds (diagnostic) |
| Last transition to online | Timestamp of the most recent offline-to-online transition |
| Last transition to offline | Timestamp of the most recent online-to-offline transition |
| Consecutive failures | Number of consecutive polling cycles where all targets failed |

## How it works

The integration considers the network **online** if **any** of the 3 targets responds to a ping. **All** targets must fail (including retries) to transition to offline. This avoids false offline triggers caused by a single target being temporarily unreachable.

DNS resolution is performed before pinging, with results cached (1-hour TTL), so hostnames work reliably without blocking the event loop.

The ping method is auto-detected at startup: privileged ICMP, unprivileged ICMP, or subprocess fallback, depending on what the system allows.

## Requirements

- Home Assistant 2024.5.0 or newer

## License

MIT
