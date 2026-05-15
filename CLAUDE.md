IMPORTANT! All python, python3, pip, pip3, pytest and other python related commands must be run inside virtual environment. Run:
```
WORKON_HOME="/home/pbrezina/workspace/.venvs" workon ha-check-online && <command to execute>
```

IMPORTANT! Use the "workon" command to load the environment, do not use "source".

## Project Overview

HACS-installable Home Assistant custom integration that monitors network connectivity by pinging 3 configurable targets. Exposes a primary `binary_sensor.online` entity (on = network up, off = network down) with retry-based state transitions to avoid false positives.

Design spec: `docs/superpowers/specs/2026-05-14-check-online-design.md`
Implementation plan: `docs/superpowers/plans/2026-05-14-check-online.md`

## Development

- **Formatter/Linter:** ruff (not black). 120 line length, double quotes, 4 spaces, alphabetical imports with force-sort-within-sections.
- **Type checking:** mypy strict mode. `python_version = "3.14"` in pyproject.toml because the installed HA package uses Python 3.13+ type parameter defaults syntax; setting it lower makes mypy reject HA's own code.
- **Tests:** pytest + pytest-asyncio + pytest-homeassistant-custom-component. Run `pytest tests/ -v`. Tox environments: `lint`, `typecheck`, `test`, `format`.

## Architectural Decisions

### icmplib version is `>=3.0`, not pinned

HA's Docker container ships its own `icmplib` (e.g. 3.0) as a system package. Pinning `==3.0.4` caused HA to try overwriting it, which failed with permission errors. Using `>=3.0` lets HA use whatever version is already installed.

### Config stored in `entry.options`, not `entry.data`

All configuration (targets, intervals, retry settings, ping timeout) lives in `entry.options` so the options flow can modify settings without recreating the config entry. `entry.data` is empty `{}`.

### Manual update listener instead of `OptionsFlowWithReload`

The design spec mentions `OptionsFlowWithReload`, but it may not be available in the target HA version (2024.5+). Instead, we use the manual pattern: `entry.async_on_unload(entry.add_update_listener(_async_update_listener))` where the listener calls `hass.config_entries.async_reload()`. This works on all HA versions.

### `single_config_entry: true` in manifest

HA's framework prevents duplicate entries at the platform level before any flow handler runs. This means `_async_abort_entries_match()` in `async_step_import` is technically redundant (HA aborts with `"single_instance_allowed"` first), but it's kept as defense-in-depth.

### Ping privilege detection runs once, cached in `hass.data`

`detect_ping_mode()` probes icmplib privileged, unprivileged, then subprocess fallback. The result is cached in `hass.data[DOMAIN]["ping_mode"]` so it survives reloads (triggered by options changes). `async_unload_entry` intentionally does NOT clean up `hass.data[DOMAIN]` to preserve this cache.

### DNS resolution happens before pinging

The coordinator calls `_resolve_and_ping()` per target, which resolves DNS first then pings the resulting IP. This avoids passing hostnames to icmplib (which has known DNS issues in HA's event loop). DNS results are cached with a configurable TTL (default 1 hour). DNS failure for a target is treated as a ping failure for that target.

### State machine: "any alive" = online

The coordinator considers the network online if ANY of the 3 targets responds. ALL targets must fail (including retries) to transition to offline. This avoids false offline triggers from a single target being down.

### `hass.data[DOMAIN]` is never cleaned up on unload

This is intentional. The cached ping mode and timestamps remain valid across reloads. Since `single_config_entry: true` only allows one entry, there's no risk of stale per-entry data accumulating.

### `last_online`/`last_offline` timestamps cached in `hass.data[DOMAIN]`

The coordinator stores `_last_online` and `_last_offline` as properties backed by `hass.data[DOMAIN]` instead of plain instance variables. This ensures timestamps survive integration reloads (triggered by options changes) without persisting across HA restarts. Without this, opening the integration settings and submitting (even without changes) would recreate the coordinator and reset both sensors to "unknown."

## Test Patterns

### `_enable_custom_integrations` fixture

All test files that set up the integration via `hass.config_entries.async_setup()` need this autouse fixture:
```python
@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations in all tests in this module."""
```
Without it, HA's test harness won't discover custom integrations.

### `_mock_setup_entry` fixture in config flow tests

Config flow tests patch `async_setup_entry` with an `AsyncMock` to prevent the real setup from running (which would call `detect_ping_mode()` and open raw sockets, blocked by the test harness socket guard).

### Entity/sensor tests use patched setup

Binary sensor and sensor tests create a `MockConfigEntry`, set `entry.runtime_data` to a mock coordinator, then call `hass.config_entries.async_setup()` with a patched `async_setup_entry`. This avoids the full integration lifecycle while still testing entity registration and state.

### Coordinator state machine tests mock `_ping_all_targets`

State machine tests (online/offline transitions, retries) mock `coordinator._ping_all_targets` directly to control what results the state machine sees. DNS integration tests mock `mock_dns.resolve` and `mock_ping.ping` individually.
