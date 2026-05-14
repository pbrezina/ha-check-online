# Check Online — Home Assistant Custom Integration Design

## Overview

A HACS-installable Home Assistant custom integration that monitors network connectivity by pinging configurable targets. Exposes a primary `binary_sensor.online` entity (on = network up, off = network down) with retry-based state transitions to avoid false positives from transient failures.

## Repository & File Structure

```
ha-check-online/
  hacs.json
  tox.ini
  pyproject.toml
  requirements_test.txt
  custom_components/
    check_online/
      __init__.py          # Integration setup, privilege detection
      manifest.json        # Integration metadata
      config_flow.py       # UI config flow + options flow + YAML import
      coordinator.py       # DataUpdateCoordinator with online/offline state machine
      helpers.py           # Ping helpers (icmplib + subprocess fallback), DNS resolver
      const.py             # Constants and defaults
      entity.py            # Base entity class (shared DeviceInfo)
      binary_sensor.py     # "Online" + per-target status binary sensors
      sensor.py            # RTT, last_online, consecutive_failures sensors
      strings.json         # UI translation strings
  tests/
    __init__.py
    conftest.py            # Shared fixtures
    test_config_flow.py
    test_coordinator.py
    test_helpers.py
    test_binary_sensor.py
    test_sensor.py
```

## Configuration

### Config Flow (Initial Setup)

The config flow asks for three ping targets:

| Field | Type | Default | Description |
|---|---|---|---|
| `target_1` | string | `8.8.8.8` | First ping target (IP or hostname) |
| `target_2` | string | `1.1.1.1` | Second ping target |
| `target_3` | string | `9.9.9.9` | Third ping target |

### Options Flow (Reconfigurable)

All settings are changeable at runtime via the options flow. Uses `OptionsFlowWithReload` for automatic integration reload on change.

| Field | Type | Default | Description |
|---|---|---|---|
| `target_1` | string | (current) | First ping target |
| `target_2` | string | (current) | Second ping target |
| `target_3` | string | (current) | Third ping target |
| `scan_interval` | int (seconds) | 60 | Ping interval when online |
| `offline_interval` | int (seconds) | 30 | Ping interval when offline |
| `retry_delay` | int (seconds) | 5 | Wait between retries on failure |
| `retry_count` | int | 2 | Number of retries before going offline |
| `ping_timeout` | int (ms) | 500 | ICMP response timeout per ping |

### YAML Configuration

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

YAML config is imported into a config entry via `async_step_import`, so both paths converge on `async_setup_entry()`. The import step maps `targets` (list) to `target_1`, `target_2`, `target_3` (individual fields). Config is stored in `entry.options` (not `entry.data`) to allow the options flow to modify settings without recreating the entry.

## DNS Resolution with TTL Cache

Implemented in `helpers.py`. Handles the case where ping targets are hostnames rather than IP addresses.

- On first use and when TTL expires, resolve the hostname via `socket.getaddrinfo` (run in executor to avoid blocking the event loop).
- Cache the resolved IP and TTL. Default TTL is 3600 seconds (1 hour) when DNS response TTL is unavailable.
- When pinging, always pass the cached IP address to `icmplib`, never the raw hostname.
- If DNS resolution fails, treat that target as if the ping failed (target is "down"). Discard the cached IP so we do not ping a stale address.
- If the target is already an IP address, skip DNS resolution entirely.

## Ping Layer

### Privilege Detection

Runs once in `async_setup()` and stores the result in `hass.data[DOMAIN]`:

1. Try `icmplib.async_ping("127.0.0.1", count=0, timeout=0, privileged=True)` — if it works, use privileged raw sockets.
2. If `SocketPermissionError`, try with `privileged=False` — if it works, use unprivileged ICMP (kernel-managed `SOCK_DGRAM`).
3. If both fail (e.g., Docker/LXC restrictions), fall back to subprocess `ping` command.

### Ping Execution

- **icmplib path:** Uses `icmplib.async_ping(ip, count=1, timeout=ping_timeout_sec, privileged=...)` per target. All 3 targets are pinged concurrently via `asyncio.gather()`.
- **Subprocess fallback:** Runs `ping -c 1 -W <timeout> <ip>` via `asyncio.create_subprocess_exec()`, parses output for success/RTT.
- Returns per-target results: `is_alive` (bool) and `rtt` (float in ms, or `None` if down).

## Coordinator & State Machine

Subclasses `DataUpdateCoordinator[CheckOnlineResult]` in `coordinator.py`.

### State Machine Logic (`_async_update_data`)

```
ONLINE state (update_interval = scan_interval):
  1. Ping all 3 targets concurrently
  2. If ANY target responds -> stay ONLINE, return results
  3. If ALL fail -> enter retry loop:
     a. Wait retry_delay seconds (asyncio.sleep)
     b. Ping all 3 again
     c. If ANY responds -> stay ONLINE, return results
     d. Repeat up to retry_count times
  4. If all retries exhausted -> transition to OFFLINE
     - Set update_interval = offline_interval

OFFLINE state (update_interval = offline_interval):
  1. Ping all 3 targets concurrently
  2. If ANY target responds -> transition to ONLINE
     - Set update_interval = scan_interval
  3. If ALL fail -> stay OFFLINE
```

The retry delays use `asyncio.sleep()` so HA's event loop is not blocked. The coordinator simply takes longer to return results during retries (~10-12 seconds with default settings). The next update is scheduled after the current one completes.

### Data Model

```python
@dataclass(frozen=True)
class TargetResult:
    is_alive: bool
    rtt: float | None  # milliseconds, None if down

@dataclass(frozen=True)
class CheckOnlineResult:
    is_online: bool
    target_results: dict[str, TargetResult]  # keyed by configured target address
    consecutive_failures: int
    last_online: datetime | None
```

## Entities

All entities inherit from `CheckOnlineEntity(CoordinatorEntity)` in `entity.py`, which provides:

- Shared `DeviceInfo` with `identifiers={(DOMAIN, entry.entry_id)}`
- `_attr_has_entity_name = True`

### Binary Sensors

| Entity name | Key | Device class | Enabled | Category |
|---|---|---|---|---|
| Online | `online` | `CONNECTIVITY` | Yes | — |
| Target 1 status | `target_1_status` | `CONNECTIVITY` | No | `DIAGNOSTIC` |
| Target 2 status | `target_2_status` | `CONNECTIVITY` | No | `DIAGNOSTIC` |
| Target 3 status | `target_3_status` | `CONNECTIVITY` | No | `DIAGNOSTIC` |

### Sensors

| Entity name | Key | Unit | Device class | State class | Enabled | Category |
|---|---|---|---|---|---|---|
| Target 1 RTT | `target_1_rtt` | ms | `DURATION` | `MEASUREMENT` | No | `DIAGNOSTIC` |
| Target 2 RTT | `target_2_rtt` | ms | `DURATION` | `MEASUREMENT` | No | `DIAGNOSTIC` |
| Target 3 RTT | `target_3_rtt` | ms | `DURATION` | `MEASUREMENT` | No | `DIAGNOSTIC` |
| Last online | `last_online` | — | `TIMESTAMP` | — | No | `DIAGNOSTIC` |
| Consecutive failures | `consecutive_failures` | — | — | `MEASUREMENT` | No | `DIAGNOSTIC` |

Disabled-by-default entities use `_attr_entity_registry_enabled_default = False`. Entity descriptor dataclasses with `value_fn` lambdas extract values from `CheckOnlineResult`.

## Integration Lifecycle

### `async_setup(hass, config)`

1. If YAML config exists, trigger import flow via `async_step_import`.

Note: `async_setup` is only called when there is YAML configuration. Privilege detection is handled in `async_setup_entry` instead, so it works regardless of whether YAML is used.

### `async_setup_entry(hass, entry)`

1. Run one-time icmplib privilege detection (cached in `hass.data[DOMAIN]` so it only runs for the first entry).
2. Create DNS resolver and ping helper (using detected privilege level).
3. Create `CheckOnlineCoordinator`.
4. `await coordinator.async_config_entry_first_refresh()`.
5. `entry.runtime_data = coordinator`.
6. Forward setup to `binary_sensor` and `sensor` platforms.

### `async_unload_entry(hass, entry)`

1. Unload platforms via `async_unload_platforms(entry, PLATFORMS)`.

## Development Environment

Use the project's virtual environment for all commands (pytest, ruff, mypy, etc.):

```bash
WORKON_HOME=/home/pbrezina/workspace/.venvs workon ha-check-online
```

The venv lives at `/home/pbrezina/workspace/.venvs/ha-check-online`. Always source this before running tests or linting. Note: `$MY_WORKSPACE` resolves to `/home/pbrezina/workspace`.

## Tooling & Code Quality

### Code Style

- **ruff** for formatting and linting (replaces black + flake8 + isort)
- Line length: 120
- Indent: 4 spaces
- Quote style: double quotes (`"`)
- Import sorting: alphabetical, force-sort-within-sections

### Type Checking

- **mypy** in strict mode
- All code uses type hints

### Testing

- **pytest** + **pytest-asyncio** + **pytest-homeassistant-custom-component**

| Test file | Covers |
|---|---|
| `test_config_flow.py` | Config flow user step, options flow, YAML import, validation errors, duplicate abort |
| `test_coordinator.py` | State machine transitions, retry logic, interval switching, DNS TTL expiry, DNS failure handling |
| `test_helpers.py` | Ping helpers (icmplib + subprocess), privilege detection, DNS resolver with TTL caching |
| `test_binary_sensor.py` | Binary sensor states, entity attributes, disabled-by-default behavior |
| `test_sensor.py` | Sensor values, unavailable states, timestamp formatting |

### tox.ini

Environments:

- `lint` — runs `ruff check` and `ruff format --check`
- `typecheck` — runs `mypy`
- `test` — runs `pytest`

## HACS Compatibility

- `hacs.json` in repo root with `name`, `homeassistant` minimum version (`2024.5.0`).
- `manifest.json` includes required fields: `domain`, `name`, `version`, `documentation`, `issue_tracker`, `codeowners`, `config_flow: true`, `iot_class: "local_polling"`, `integration_type: "service"`, `requirements: ["icmplib==3.0.4"]`.
- Single integration per repository.
- `custom_components/check_online/` directory structure.
