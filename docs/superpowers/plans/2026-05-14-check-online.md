# Check Online Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a HACS-installable Home Assistant custom integration that monitors network connectivity by pinging 3 configurable targets, with retry logic and online/offline state machine.

**Architecture:** DataUpdateCoordinator with an internal online/offline state machine. DNS resolution is cached with TTL. Pinging uses icmplib (async, unprivileged) with subprocess fallback. Config flow + YAML import both converge on `async_setup_entry`.

**Tech Stack:** Python 3.12+, Home Assistant 2024.5+, icmplib 3.0, pytest + pytest-homeassistant-custom-component, ruff, mypy

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `tox.ini`
- Create: `requirements_test.txt`
- Create: `hacs.json`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "ha-check-online"
version = "1.0.0"
requires-python = ">=3.12"

[tool.ruff]
line-length = 120
indent-width = 4

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "SIM", "RUF"]

[tool.ruff.lint.isort]
force-sort-within-sections = true

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = [
    "icmplib.*",
    "homeassistant.*",
    "pytest_homeassistant_custom_component.*",
    "voluptuous",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create `tox.ini`**

```ini
[tox]
envlist = lint,typecheck,test
skipsdist = true

[testenv:lint]
deps =
    ruff
commands =
    ruff check custom_components/ tests/
    ruff format --check custom_components/ tests/

[testenv:typecheck]
deps =
    mypy
    homeassistant
    icmplib
commands =
    mypy custom_components/

[testenv:test]
deps =
    -r requirements_test.txt
commands =
    pytest {posargs}

[testenv:format]
deps =
    ruff
commands =
    ruff check --fix custom_components/ tests/
    ruff format custom_components/ tests/
```

- [ ] **Step 3: Create `requirements_test.txt`**

```
pytest>=8.0
pytest-asyncio>=0.23
pytest-homeassistant-custom-component>=0.13
mypy>=1.10
ruff>=0.4
icmplib>=3.0
```

- [ ] **Step 4: Create `hacs.json`**

```json
{
  "name": "Check Online",
  "homeassistant": "2024.5.0"
}
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tox.ini requirements_test.txt hacs.json
git commit -m "Add project scaffolding: pyproject.toml, tox.ini, requirements, hacs.json"
```

---

### Task 2: Integration Skeleton

**Files:**
- Create: `custom_components/check_online/manifest.json`
- Create: `custom_components/check_online/const.py`
- Create: `custom_components/check_online/__init__.py` (minimal)
- Create: `custom_components/check_online/strings.json`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `custom_components/check_online/manifest.json`**

```json
{
  "domain": "check_online",
  "name": "Check Online",
  "version": "1.0.0",
  "codeowners": [],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/pbrezina/ha-check-online",
  "issue_tracker": "https://github.com/pbrezina/ha-check-online/issues",
  "iot_class": "local_polling",
  "integration_type": "service",
  "single_config_entry": true,
  "requirements": ["icmplib==3.0.4"]
}
```

- [ ] **Step 2: Create `custom_components/check_online/const.py`**

```python
"""Constants for the Check Online integration."""

from homeassistant.const import Platform

DOMAIN = "check_online"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]

CONF_TARGET_1 = "target_1"
CONF_TARGET_2 = "target_2"
CONF_TARGET_3 = "target_3"
CONF_TARGETS = "targets"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_OFFLINE_INTERVAL = "offline_interval"
CONF_RETRY_DELAY = "retry_delay"
CONF_RETRY_COUNT = "retry_count"
CONF_PING_TIMEOUT = "ping_timeout"

DEFAULT_TARGET_1 = "8.8.8.8"
DEFAULT_TARGET_2 = "1.1.1.1"
DEFAULT_TARGET_3 = "9.9.9.9"
DEFAULT_SCAN_INTERVAL = 60
DEFAULT_OFFLINE_INTERVAL = 30
DEFAULT_RETRY_DELAY = 5
DEFAULT_RETRY_COUNT = 2
DEFAULT_PING_TIMEOUT = 500
DEFAULT_DNS_TTL = 3600
```

- [ ] **Step 3: Create minimal `custom_components/check_online/__init__.py`**

This is a placeholder that will be fully implemented in Task 9. It needs to exist so the integration is discoverable by tests.

```python
"""The Check Online integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Check Online from a config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
```

- [ ] **Step 4: Create `custom_components/check_online/strings.json`**

This contains all translation strings for config flow UI and entity names. Written now because it is referenced by config flow and entity tests.

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Set up Check Online",
        "description": "Configure the ping targets to monitor network connectivity.",
        "data": {
          "target_1": "Target 1 (IP or hostname)",
          "target_2": "Target 2 (IP or hostname)",
          "target_3": "Target 3 (IP or hostname)"
        }
      }
    },
    "abort": {
      "already_configured": "Check Online is already configured."
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "Check Online Options",
        "data": {
          "target_1": "Target 1 (IP or hostname)",
          "target_2": "Target 2 (IP or hostname)",
          "target_3": "Target 3 (IP or hostname)",
          "scan_interval": "Scan interval when online (seconds)",
          "offline_interval": "Scan interval when offline (seconds)",
          "retry_delay": "Retry delay (seconds)",
          "retry_count": "Retry count before going offline",
          "ping_timeout": "Ping timeout (milliseconds)"
        }
      }
    }
  },
  "entity": {
    "binary_sensor": {
      "online": {
        "name": "Online"
      },
      "target_1_status": {
        "name": "Target 1 status"
      },
      "target_2_status": {
        "name": "Target 2 status"
      },
      "target_3_status": {
        "name": "Target 3 status"
      }
    },
    "sensor": {
      "target_1_rtt": {
        "name": "Target 1 RTT"
      },
      "target_2_rtt": {
        "name": "Target 2 RTT"
      },
      "target_3_rtt": {
        "name": "Target 3 RTT"
      },
      "last_online": {
        "name": "Last online"
      },
      "consecutive_failures": {
        "name": "Consecutive failures"
      }
    }
  }
}
```

- [ ] **Step 5: Create `tests/__init__.py` and `tests/conftest.py`**

`tests/__init__.py`:
```python
```

`tests/conftest.py`:
```python
"""Shared test fixtures for check_online."""

from __future__ import annotations

from typing import Any

import pytest

from custom_components.check_online.const import (
    CONF_OFFLINE_INTERVAL,
    CONF_PING_TIMEOUT,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    DEFAULT_OFFLINE_INTERVAL,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_1,
    DEFAULT_TARGET_2,
    DEFAULT_TARGET_3,
)

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture
def default_options() -> dict[str, Any]:
    """Return default configuration options."""
    return {
        CONF_TARGET_1: DEFAULT_TARGET_1,
        CONF_TARGET_2: DEFAULT_TARGET_2,
        CONF_TARGET_3: DEFAULT_TARGET_3,
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_OFFLINE_INTERVAL: DEFAULT_OFFLINE_INTERVAL,
        CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
        CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
        CONF_PING_TIMEOUT: DEFAULT_PING_TIMEOUT,
    }
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/ tests/
git commit -m "Add integration skeleton: manifest, constants, strings, test fixtures"
```

---

### Task 3: DNS Resolver

**Files:**
- Create: `custom_components/check_online/helpers.py`
- Create: `tests/test_helpers.py`

- [ ] **Step 1: Write failing tests for DnsResolver**

Create `tests/test_helpers.py`:

```python
"""Tests for check_online helpers."""

from __future__ import annotations

import socket
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.check_online.helpers import DnsResolver


class TestDnsResolver:
    """Tests for DNS resolver with TTL cache."""

    async def test_resolve_ip_address_passthrough(self) -> None:
        """IP addresses should be returned as-is without DNS lookup."""
        hass = MagicMock()
        resolver = DnsResolver(hass)

        result = await resolver.resolve("8.8.8.8")

        assert result == "8.8.8.8"
        hass.async_add_executor_job.assert_not_called()

    async def test_resolve_ipv6_address_passthrough(self) -> None:
        """IPv6 addresses should be returned as-is without DNS lookup."""
        hass = MagicMock()
        resolver = DnsResolver(hass)

        result = await resolver.resolve("2001:4860:4860::8888")

        assert result == "2001:4860:4860::8888"
        hass.async_add_executor_job.assert_not_called()

    async def test_resolve_hostname_success(self) -> None:
        """Hostname should be resolved via getaddrinfo."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass)

        result = await resolver.resolve("example.com")

        assert result == "93.184.216.34"

    async def test_resolve_hostname_cached(self) -> None:
        """Second call within TTL should use cache, not call getaddrinfo."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=3600)

        await resolver.resolve("example.com")
        await resolver.resolve("example.com")

        assert hass.async_add_executor_job.call_count == 1

    async def test_resolve_hostname_cache_expired(self) -> None:
        """After TTL expires, should resolve again."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=1)

        await resolver.resolve("example.com")

        with patch("custom_components.check_online.helpers.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2
            await resolver.resolve("example.com")

        assert hass.async_add_executor_job.call_count == 2

    async def test_resolve_hostname_failure_returns_none(self) -> None:
        """DNS failure should return None."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(side_effect=socket.gaierror)
        resolver = DnsResolver(hass)

        result = await resolver.resolve("nonexistent.invalid")

        assert result is None

    async def test_resolve_hostname_failure_clears_cache(self) -> None:
        """DNS failure should clear any previously cached entry."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(
            return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))
            ]
        )
        resolver = DnsResolver(hass, ttl=1)

        # First resolve succeeds
        result = await resolver.resolve("example.com")
        assert result == "93.184.216.34"

        # Expire cache
        with patch("custom_components.check_online.helpers.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 2
            # Second resolve fails
            hass.async_add_executor_job = AsyncMock(side_effect=socket.gaierror)
            result = await resolver.resolve("example.com")

        assert result is None

    async def test_resolve_empty_result_returns_none(self) -> None:
        """Empty getaddrinfo result should return None."""
        hass = MagicMock()
        hass.async_add_executor_job = AsyncMock(return_value=[])
        resolver = DnsResolver(hass)

        result = await resolver.resolve("example.com")

        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_helpers.py -v`
Expected: FAIL — `DnsResolver` does not exist yet.

- [ ] **Step 3: Implement DnsResolver in `custom_components/check_online/helpers.py`**

```python
"""Helpers for the Check Online integration."""

from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import dataclass

from homeassistant.core import HomeAssistant

from .const import DEFAULT_DNS_TTL


@dataclass
class DnsCacheEntry:
    """A cached DNS resolution result."""

    ip_address: str
    expires_at: float


class DnsResolver:
    """Resolve hostnames to IP addresses with TTL-based caching."""

    def __init__(self, hass: HomeAssistant, ttl: int = DEFAULT_DNS_TTL) -> None:
        self._hass = hass
        self._ttl = ttl
        self._cache: dict[str, DnsCacheEntry] = {}

    def _is_ip_address(self, host: str) -> bool:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True

    async def resolve(self, host: str) -> str | None:
        """Resolve a hostname to an IP address.

        Returns the IP directly if host is already an IP address.
        Returns None if DNS resolution fails.
        """
        if self._is_ip_address(host):
            return host

        cached = self._cache.get(host)
        if cached is not None and cached.expires_at > time.monotonic():
            return cached.ip_address

        try:
            result = await self._hass.async_add_executor_job(
                socket.getaddrinfo, host, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except socket.gaierror:
            self._cache.pop(host, None)
            return None

        if not result:
            self._cache.pop(host, None)
            return None

        ip = result[0][4][0]
        self._cache[host] = DnsCacheEntry(
            ip_address=ip,
            expires_at=time.monotonic() + self._ttl,
        )
        return ip
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_helpers.py::TestDnsResolver -v`
Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/check_online/helpers.py tests/test_helpers.py
git commit -m "Add DNS resolver with TTL-based caching"
```

---

### Task 4: Ping Helpers

**Files:**
- Modify: `custom_components/check_online/helpers.py`
- Modify: `tests/test_helpers.py`

- [ ] **Step 1: Write failing tests for ping helpers**

Append to `tests/test_helpers.py`:

```python
from custom_components.check_online.helpers import (
    DnsResolver,
    PingHelper,
    PingMode,
    PingResult,
    detect_ping_mode,
    ping_icmplib,
    ping_subprocess,
)


class TestPingResult:
    """Tests for PingResult dataclass."""

    def test_alive_with_rtt(self) -> None:
        result = PingResult(is_alive=True, rtt=12.3)
        assert result.is_alive is True
        assert result.rtt == 12.3

    def test_dead_with_no_rtt(self) -> None:
        result = PingResult(is_alive=False, rtt=None)
        assert result.is_alive is False
        assert result.rtt is None


class TestDetectPingMode:
    """Tests for privilege detection."""

    async def test_privileged_mode(self) -> None:
        """When privileged ping works, return PRIVILEGED."""
        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.PRIVILEGED

    async def test_unprivileged_mode(self) -> None:
        """When privileged fails but unprivileged works, return UNPRIVILEGED."""
        from icmplib import SocketPermissionError

        async def mock_ping(*args: object, **kwargs: object) -> None:
            if kwargs.get("privileged", True):
                raise SocketPermissionError

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            side_effect=mock_ping,
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.UNPRIVILEGED

    async def test_subprocess_fallback(self) -> None:
        """When both privileged and unprivileged fail, return SUBPROCESS."""
        from icmplib import SocketPermissionError

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            side_effect=SocketPermissionError,
        ):
            mode = await detect_ping_mode()
            assert mode == PingMode.SUBPROCESS


class TestPingIcmplib:
    """Tests for icmplib-based ping."""

    async def test_success(self) -> None:
        mock_host = MagicMock()
        mock_host.is_alive = True
        mock_host.avg_rtt = 12.3

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            return_value=mock_host,
        ):
            result = await ping_icmplib("8.8.8.8", 500, privileged=False)

        assert result.is_alive is True
        assert result.rtt == 12.3

    async def test_failure(self) -> None:
        mock_host = MagicMock()
        mock_host.is_alive = False

        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            return_value=mock_host,
        ):
            result = await ping_icmplib("192.168.1.1", 500, privileged=False)

        assert result.is_alive is False
        assert result.rtt is None

    async def test_exception_returns_dead(self) -> None:
        with patch(
            "custom_components.check_online.helpers.icmplib_async_ping",
            new_callable=AsyncMock,
            side_effect=Exception("socket error"),
        ):
            result = await ping_icmplib("8.8.8.8", 500, privileged=False)

        assert result.is_alive is False
        assert result.rtt is None


class TestPingSubprocess:
    """Tests for subprocess-based ping."""

    async def test_success(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate.return_value = (
            b"64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=12.3 ms\n",
            b"",
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ping_subprocess("8.8.8.8", 500)

        assert result.is_alive is True
        assert result.rtt == 12.3

    async def test_failure(self) -> None:
        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate.return_value = (b"", b"")

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await ping_subprocess("192.168.1.1", 500)

        assert result.is_alive is False
        assert result.rtt is None

    async def test_exception_returns_dead(self) -> None:
        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=OSError("ping not found"),
        ):
            result = await ping_subprocess("8.8.8.8", 500)

        assert result.is_alive is False
        assert result.rtt is None


class TestPingHelper:
    """Tests for PingHelper orchestration."""

    async def test_ping_uses_icmplib_privileged(self) -> None:
        helper = PingHelper(PingMode.PRIVILEGED, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500, privileged=True)

    async def test_ping_uses_icmplib_unprivileged(self) -> None:
        helper = PingHelper(PingMode.UNPRIVILEGED, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500, privileged=False)

    async def test_ping_uses_subprocess(self) -> None:
        helper = PingHelper(PingMode.SUBPROCESS, timeout_ms=500)

        with patch(
            "custom_components.check_online.helpers.ping_subprocess",
            new_callable=AsyncMock,
            return_value=PingResult(is_alive=True, rtt=10.0),
        ) as mock:
            result = await helper.ping("8.8.8.8")

        assert result.is_alive is True
        mock.assert_called_once_with("8.8.8.8", 500)

    async def test_ping_all_concurrent(self) -> None:
        helper = PingHelper(PingMode.UNPRIVILEGED, timeout_ms=500)

        call_order: list[str] = []

        async def mock_ping_icmplib(ip: str, timeout_ms: int, privileged: bool) -> PingResult:
            call_order.append(ip)
            return PingResult(is_alive=True, rtt=10.0)

        with patch(
            "custom_components.check_online.helpers.ping_icmplib",
            side_effect=mock_ping_icmplib,
        ):
            results = await helper.ping_all(["8.8.8.8", "1.1.1.1", "9.9.9.9"])

        assert len(results) == 3
        assert all(r.is_alive for r in results.values())
        assert set(results.keys()) == {"8.8.8.8", "1.1.1.1", "9.9.9.9"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_helpers.py -v -k "not TestDnsResolver"`
Expected: FAIL — ping functions do not exist yet.

- [ ] **Step 3: Implement ping helpers in `custom_components/check_online/helpers.py`**

Add these imports at the top of `helpers.py` (after existing imports):

```python
import asyncio
import enum
import logging
import re

from icmplib import async_ping as icmplib_async_ping
from icmplib import SocketPermissionError as IcmpSocketPermissionError
```

Add these classes and functions after the `DnsResolver` class:

```python
_LOGGER = logging.getLogger(__name__)


class PingMode(enum.Enum):
    """How to send ICMP pings."""

    PRIVILEGED = "privileged"
    UNPRIVILEGED = "unprivileged"
    SUBPROCESS = "subprocess"


@dataclass(frozen=True)
class PingResult:
    """Result of a single ping attempt."""

    is_alive: bool
    rtt: float | None  # milliseconds


async def detect_ping_mode() -> PingMode:
    """Detect the best available ping method.

    Tries privileged icmplib, then unprivileged, then falls back to subprocess.
    """
    try:
        await icmplib_async_ping("127.0.0.1", count=0, timeout=0, privileged=True)
        return PingMode.PRIVILEGED
    except IcmpSocketPermissionError:
        pass

    try:
        await icmplib_async_ping("127.0.0.1", count=0, timeout=0, privileged=False)
        return PingMode.UNPRIVILEGED
    except IcmpSocketPermissionError:
        pass

    return PingMode.SUBPROCESS


async def ping_icmplib(ip: str, timeout_ms: int, *, privileged: bool) -> PingResult:
    """Ping a host using icmplib."""
    try:
        result = await icmplib_async_ping(
            ip,
            count=1,
            timeout=timeout_ms / 1000.0,
            privileged=privileged,
        )
        return PingResult(
            is_alive=result.is_alive,
            rtt=result.avg_rtt if result.is_alive else None,
        )
    except Exception:
        _LOGGER.debug("icmplib ping failed for %s", ip, exc_info=True)
        return PingResult(is_alive=False, rtt=None)


async def ping_subprocess(ip: str, timeout_ms: int) -> PingResult:
    """Ping a host using the system ping command."""
    timeout_sec = max(1, round(timeout_ms / 1000))
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping",
            "-c",
            "1",
            "-W",
            str(timeout_sec),
            ip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec + 5)
        if proc.returncode == 0:
            match = re.search(r"time[=<](\d+\.?\d*)", stdout.decode())
            rtt = float(match.group(1)) if match else None
            return PingResult(is_alive=True, rtt=rtt)
    except Exception:
        _LOGGER.debug("Subprocess ping failed for %s", ip, exc_info=True)

    return PingResult(is_alive=False, rtt=None)


class PingHelper:
    """Ping hosts using the detected best method."""

    def __init__(self, mode: PingMode, timeout_ms: int) -> None:
        self._mode = mode
        self._timeout_ms = timeout_ms

    async def ping(self, ip: str) -> PingResult:
        """Ping a single IP address."""
        if self._mode == PingMode.SUBPROCESS:
            return await ping_subprocess(ip, self._timeout_ms)
        return await ping_icmplib(
            ip,
            self._timeout_ms,
            privileged=(self._mode == PingMode.PRIVILEGED),
        )

    async def ping_all(self, ips: list[str]) -> dict[str, PingResult]:
        """Ping multiple IPs concurrently. Returns results keyed by IP."""
        results = await asyncio.gather(*(self.ping(ip) for ip in ips))
        return dict(zip(ips, results))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_helpers.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/check_online/helpers.py tests/test_helpers.py
git commit -m "Add ping helpers with icmplib, subprocess fallback, and privilege detection"
```

---

### Task 5: Coordinator with State Machine

**Files:**
- Create: `custom_components/check_online/coordinator.py`
- Create: `tests/test_coordinator.py`

- [ ] **Step 1: Write failing tests for the coordinator**

Create `tests/test_coordinator.py`:

```python
"""Tests for CheckOnlineCoordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import (
    CONF_OFFLINE_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    DOMAIN,
)
from custom_components.check_online.coordinator import (
    CheckOnlineCoordinator,
    TargetResult,
)
from custom_components.check_online.helpers import DnsResolver, PingHelper, PingResult


def _make_coordinator(
    hass: HomeAssistant,
    options: dict[str, Any],
) -> tuple[CheckOnlineCoordinator, MagicMock, MagicMock]:
    """Create a coordinator with mocked helpers.

    State machine tests should mock coordinator._ping_all_targets directly.
    DNS integration tests should mock mock_dns.resolve and mock_ping.ping.
    """
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options)
    entry.add_to_hass(hass)

    mock_ping = MagicMock(spec=PingHelper)
    mock_ping.ping = AsyncMock(return_value=PingResult(is_alive=True, rtt=10.0))

    mock_dns = MagicMock(spec=DnsResolver)
    mock_dns.resolve = AsyncMock(side_effect=lambda x: x)

    coordinator = CheckOnlineCoordinator(
        hass=hass,
        config_entry=entry,
        ping_helper=mock_ping,
        dns_resolver=mock_dns,
    )
    return coordinator, mock_ping, mock_dns


def _all_alive(options: dict[str, Any]) -> dict[str, TargetResult]:
    return {
        options[CONF_TARGET_1]: TargetResult(is_alive=True, rtt=10.0),
        options[CONF_TARGET_2]: TargetResult(is_alive=True, rtt=15.0),
        options[CONF_TARGET_3]: TargetResult(is_alive=True, rtt=20.0),
    }


def _all_dead(options: dict[str, Any]) -> dict[str, TargetResult]:
    return {
        options[CONF_TARGET_1]: TargetResult(is_alive=False, rtt=None),
        options[CONF_TARGET_2]: TargetResult(is_alive=False, rtt=None),
        options[CONF_TARGET_3]: TargetResult(is_alive=False, rtt=None),
    }


def _one_alive(options: dict[str, Any]) -> dict[str, TargetResult]:
    return {
        options[CONF_TARGET_1]: TargetResult(is_alive=True, rtt=10.0),
        options[CONF_TARGET_2]: TargetResult(is_alive=False, rtt=None),
        options[CONF_TARGET_3]: TargetResult(is_alive=False, rtt=None),
    }


class TestOnlineState:
    """Tests for behavior when coordinator is in ONLINE state."""

    async def test_stays_online_when_all_respond(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_alive(default_options)
        )

        await coordinator.async_refresh()

        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0

    async def test_stays_online_when_one_responds(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_one_alive(default_options)
        )

        await coordinator.async_refresh()

        assert coordinator.data.is_online is True

    async def test_retries_before_going_offline(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """All pings fail -> should retry retry_count times before going offline."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_dead(default_options)
        )

        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await coordinator.async_refresh()

        assert coordinator.data.is_online is False
        assert coordinator.data.consecutive_failures == 1
        # Initial ping + retry_count retries = 3 total _ping_all_targets calls
        assert coordinator._ping_all_targets.call_count == 3
        # retry_count sleeps of retry_delay seconds
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(default_options[CONF_RETRY_DELAY])

    async def test_retry_succeeds_stays_online(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """First ping fails, retry succeeds -> stay online."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            side_effect=[_all_dead(default_options), _all_alive(default_options)]
        )

        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()

        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0

    async def test_interval_changes_to_offline(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_dead(default_options)
        )

        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()

        assert coordinator.update_interval == timedelta(
            seconds=default_options[CONF_OFFLINE_INTERVAL]
        )


class TestOfflineState:
    """Tests for behavior when coordinator is in OFFLINE state."""

    async def _go_offline(
        self,
        coordinator: CheckOnlineCoordinator,
        options: dict[str, Any],
    ) -> None:
        """Helper: drive coordinator to OFFLINE state."""
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_dead(options)
        )
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False

    async def test_goes_online_on_success(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)

        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_alive(default_options)
        )
        await coordinator.async_refresh()

        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0
        assert coordinator.update_interval == timedelta(
            seconds=default_options[CONF_SCAN_INTERVAL]
        )

    async def test_stays_offline_on_failure(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)
        failures_after_first_offline = coordinator.data.consecutive_failures

        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_dead(default_options)
        )
        await coordinator.async_refresh()

        assert coordinator.data.is_online is False
        assert coordinator.data.consecutive_failures == failures_after_first_offline + 1

    async def test_one_alive_enough_to_go_online(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)

        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_one_alive(default_options)
        )
        await coordinator.async_refresh()

        assert coordinator.data.is_online is True


class TestDnsIntegration:
    """Tests for DNS resolution within the coordinator.

    These tests do NOT mock _ping_all_targets. Instead they mock the
    underlying dns_resolver.resolve and ping_helper.ping to verify
    the coordinator handles DNS failures correctly.
    """

    async def test_dns_failure_treated_as_ping_failure(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """If DNS resolution fails for all targets, treat as all pings failed."""
        coordinator, _, mock_dns = _make_coordinator(hass, default_options)
        mock_dns.resolve = AsyncMock(return_value=None)

        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()

        assert coordinator.data.is_online is False

    async def test_dns_failure_for_one_target(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """DNS failure for one target should not bring everything offline."""
        coordinator, mock_ping, mock_dns = _make_coordinator(hass, default_options)

        async def selective_resolve(host: str) -> str | None:
            if host == default_options[CONF_TARGET_1]:
                return None
            return host

        mock_dns.resolve = AsyncMock(side_effect=selective_resolve)
        mock_ping.ping = AsyncMock(return_value=PingResult(is_alive=True, rtt=10.0))

        await coordinator.async_refresh()

        assert coordinator.data.is_online is True
        target_1_result = coordinator.data.target_results[default_options[CONF_TARGET_1]]
        assert target_1_result.is_alive is False


class TestLastOnline:
    """Tests for last_online timestamp tracking."""

    async def test_set_when_online(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_alive(default_options)
        )

        await coordinator.async_refresh()

        assert coordinator.data.last_online is not None

    async def test_preserved_when_offline(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_alive(default_options)
        )

        # Go online first
        await coordinator.async_refresh()
        last_online = coordinator.data.last_online
        assert last_online is not None

        # Go offline
        coordinator._ping_all_targets = AsyncMock(  # type: ignore[method-assign]
            return_value=_all_dead(default_options)
        )
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()

        assert coordinator.data.is_online is False
        assert coordinator.data.last_online == last_online
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_coordinator.py -v`
Expected: FAIL — `CheckOnlineCoordinator` does not exist yet.

- [ ] **Step 3: Implement the coordinator**

Create `custom_components/check_online/coordinator.py`:

```python
"""DataUpdateCoordinator for the Check Online integration."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_OFFLINE_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    DEFAULT_OFFLINE_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .helpers import DnsResolver, PingHelper, PingResult

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class TargetResult:
    """Result for a single ping target."""

    is_alive: bool
    rtt: float | None  # milliseconds


@dataclass(frozen=True)
class CheckOnlineResult:
    """Combined result of all ping checks."""

    is_online: bool
    target_results: dict[str, TargetResult]
    consecutive_failures: int
    last_online: datetime | None


class CheckOnlineCoordinator(DataUpdateCoordinator[CheckOnlineResult]):
    """Coordinator that manages online/offline state via ping checks."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        ping_helper: PingHelper,
        dns_resolver: DnsResolver,
    ) -> None:
        options = config_entry.options
        self._targets: list[str] = [
            options[CONF_TARGET_1],
            options[CONF_TARGET_2],
            options[CONF_TARGET_3],
        ]
        self._scan_interval: int = options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        self._offline_interval: int = options.get(CONF_OFFLINE_INTERVAL, DEFAULT_OFFLINE_INTERVAL)
        self._retry_delay: int = options.get(CONF_RETRY_DELAY, DEFAULT_RETRY_DELAY)
        self._retry_count: int = options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
        self._ping_helper = ping_helper
        self._dns_resolver = dns_resolver
        self._is_online: bool = True
        self._consecutive_failures: int = 0
        self._last_online: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=self._scan_interval),
        )

    async def _resolve_and_ping(self, target: str) -> tuple[str, TargetResult]:
        """Resolve DNS and ping a single target."""
        ip = await self._dns_resolver.resolve(target)
        if ip is None:
            return target, TargetResult(is_alive=False, rtt=None)

        ping_result = await self._ping_helper.ping(ip)
        return target, TargetResult(is_alive=ping_result.is_alive, rtt=ping_result.rtt)

    async def _ping_all_targets(self) -> dict[str, TargetResult]:
        """Ping all configured targets concurrently."""
        tasks = [self._resolve_and_ping(t) for t in self._targets]
        results = await asyncio.gather(*tasks)
        return dict(results)

    def _any_alive(self, results: dict[str, TargetResult]) -> bool:
        return any(r.is_alive for r in results.values())

    def _make_result(
        self, is_online: bool, target_results: dict[str, TargetResult]
    ) -> CheckOnlineResult:
        return CheckOnlineResult(
            is_online=is_online,
            target_results=target_results,
            consecutive_failures=self._consecutive_failures,
            last_online=self._last_online,
        )

    async def _async_update_data(self) -> CheckOnlineResult:
        """Fetch data: ping all targets and manage online/offline state."""
        target_results = await self._ping_all_targets()

        if self._is_online:
            return await self._handle_online_state(target_results)

        return self._handle_offline_state(target_results)

    async def _handle_online_state(
        self, target_results: dict[str, TargetResult]
    ) -> CheckOnlineResult:
        """Handle update when currently online."""
        if self._any_alive(target_results):
            self._consecutive_failures = 0
            self._last_online = dt_util.utcnow()
            return self._make_result(True, target_results)

        # All failed — retry
        for _ in range(self._retry_count):
            await asyncio.sleep(self._retry_delay)
            target_results = await self._ping_all_targets()
            if self._any_alive(target_results):
                self._consecutive_failures = 0
                self._last_online = dt_util.utcnow()
                return self._make_result(True, target_results)

        # All retries exhausted — go offline
        self._is_online = False
        self._consecutive_failures += 1
        self.update_interval = timedelta(seconds=self._offline_interval)
        _LOGGER.warning("Network is offline after %d retries", self._retry_count)
        return self._make_result(False, target_results)

    def _handle_offline_state(
        self, target_results: dict[str, TargetResult]
    ) -> CheckOnlineResult:
        """Handle update when currently offline."""
        if self._any_alive(target_results):
            self._is_online = True
            self._consecutive_failures = 0
            self._last_online = dt_util.utcnow()
            self.update_interval = timedelta(seconds=self._scan_interval)
            _LOGGER.info("Network is back online")
            return self._make_result(True, target_results)

        self._consecutive_failures += 1
        return self._make_result(False, target_results)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_coordinator.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/check_online/coordinator.py tests/test_coordinator.py
git commit -m "Add coordinator with online/offline state machine and retry logic"
```

---

### Task 6: Base Entity and Binary Sensors

**Files:**
- Create: `custom_components/check_online/entity.py`
- Create: `custom_components/check_online/binary_sensor.py`
- Create: `tests/test_binary_sensor.py`

- [ ] **Step 1: Write failing tests for binary sensors**

Create `tests/test_binary_sensor.py`:

```python
"""Tests for check_online binary sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import DOMAIN
from custom_components.check_online.coordinator import (
    CheckOnlineCoordinator,
    CheckOnlineResult,
    TargetResult,
)


def _make_result(
    is_online: bool = True,
    target_1_alive: bool = True,
    target_2_alive: bool = True,
    target_3_alive: bool = True,
) -> CheckOnlineResult:
    return CheckOnlineResult(
        is_online=is_online,
        target_results={
            "8.8.8.8": TargetResult(is_alive=target_1_alive, rtt=10.0 if target_1_alive else None),
            "1.1.1.1": TargetResult(is_alive=target_2_alive, rtt=15.0 if target_2_alive else None),
            "9.9.9.9": TargetResult(is_alive=target_3_alive, rtt=20.0 if target_3_alive else None),
        },
        consecutive_failures=0 if is_online else 1,
        last_online=datetime(2026, 1, 1),
    )


async def _setup_integration(
    hass: HomeAssistant, default_options: dict[str, Any], result: CheckOnlineResult
) -> MockConfigEntry:
    """Set up the integration with a mock coordinator."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=default_options)
    entry.add_to_hass(hass)

    mock_coordinator = MagicMock(spec=CheckOnlineCoordinator)
    mock_coordinator.data = result
    mock_coordinator.last_update_success = True
    mock_coordinator.config_entry = entry

    entry.runtime_data = mock_coordinator

    with patch(
        "custom_components.check_online.binary_sensor.CheckOnlineCoordinator",
        return_value=mock_coordinator,
    ):
        await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
        await hass.async_block_till_done()

    return entry


class TestOnlineBinarySensor:
    """Tests for the main Online binary sensor."""

    async def test_online_state_on(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result(is_online=True)
        await _setup_integration(hass, default_options, result)

        state = hass.states.get("binary_sensor.check_online_online")
        assert state is not None
        assert state.state == STATE_ON

    async def test_online_state_off(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result(is_online=False)
        await _setup_integration(hass, default_options, result)

        state = hass.states.get("binary_sensor.check_online_online")
        assert state is not None
        assert state.state == STATE_OFF

    async def test_device_class_is_connectivity(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        state = hass.states.get("binary_sensor.check_online_online")
        assert state is not None
        assert state.attributes.get("device_class") == BinarySensorDeviceClass.CONNECTIVITY

    async def test_enabled_by_default(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("binary_sensor.check_online_online")
        assert entity is not None
        assert entity.disabled_by is None


class TestTargetBinarySensors:
    """Tests for per-target status binary sensors."""

    async def test_disabled_by_default(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("binary_sensor.check_online_target_1_status")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    async def test_entity_category_diagnostic(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("binary_sensor.check_online_target_1_status")
        assert entity is not None
        assert entity.entity_category == EntityCategory.DIAGNOSTIC
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_binary_sensor.py -v`
Expected: FAIL — entity and binary_sensor modules do not exist yet.

- [ ] **Step 3: Implement `custom_components/check_online/entity.py`**

```python
"""Base entity for the Check Online integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CheckOnlineCoordinator


class CheckOnlineEntity(CoordinatorEntity[CheckOnlineCoordinator]):
    """Base class for Check Online entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Check Online",
        )
```

- [ ] **Step 4: Implement `custom_components/check_online/binary_sensor.py`**

```python
"""Binary sensor platform for the Check Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TARGET_1, CONF_TARGET_2, CONF_TARGET_3
from .coordinator import CheckOnlineCoordinator, CheckOnlineResult
from .entity import CheckOnlineEntity


@dataclass(frozen=True, kw_only=True)
class CheckOnlineBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Check Online binary sensor."""

    value_fn: Callable[[CheckOnlineResult], bool]


MAIN_BINARY_SENSOR = CheckOnlineBinarySensorDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    value_fn=lambda data: data.is_online,
)

TARGET_SENSORS: list[tuple[str, str]] = [
    (CONF_TARGET_1, "target_1_status"),
    (CONF_TARGET_2, "target_2_status"),
    (CONF_TARGET_3, "target_3_status"),
]


def _make_target_description(
    target: str, key: str
) -> CheckOnlineBinarySensorDescription:
    return CheckOnlineBinarySensorDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data, t=target: (
            data.target_results[t].is_alive if t in data.target_results else False
        ),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Check Online binary sensors."""
    coordinator: CheckOnlineCoordinator = entry.runtime_data

    descriptions: list[CheckOnlineBinarySensorDescription] = [MAIN_BINARY_SENSOR]
    for conf_key, entity_key in TARGET_SENSORS:
        target = entry.options[conf_key]
        descriptions.append(_make_target_description(target, entity_key))

    async_add_entities(
        CheckOnlineBinarySensor(coordinator, entry.entry_id, desc)
        for desc in descriptions
    )


class CheckOnlineBinarySensor(CheckOnlineEntity, BinarySensorEntity):
    """Binary sensor for Check Online."""

    entity_description: CheckOnlineBinarySensorDescription

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        description: CheckOnlineBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the network is online."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_binary_sensor.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/check_online/entity.py custom_components/check_online/binary_sensor.py tests/test_binary_sensor.py
git commit -m "Add base entity and binary sensors (online + per-target status)"
```

---

### Task 7: Sensors

**Files:**
- Create: `custom_components/check_online/sensor.py`
- Create: `tests/test_sensor.py`

- [ ] **Step 1: Write failing tests for sensors**

Create `tests/test_sensor.py`:

```python
"""Tests for check_online sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import DOMAIN
from custom_components.check_online.coordinator import (
    CheckOnlineCoordinator,
    CheckOnlineResult,
    TargetResult,
)


def _make_result(
    is_online: bool = True,
    rtt_1: float | None = 10.0,
    rtt_2: float | None = 15.0,
    rtt_3: float | None = 20.0,
    consecutive_failures: int = 0,
    last_online: datetime | None = None,
) -> CheckOnlineResult:
    return CheckOnlineResult(
        is_online=is_online,
        target_results={
            "8.8.8.8": TargetResult(is_alive=rtt_1 is not None, rtt=rtt_1),
            "1.1.1.1": TargetResult(is_alive=rtt_2 is not None, rtt=rtt_2),
            "9.9.9.9": TargetResult(is_alive=rtt_3 is not None, rtt=rtt_3),
        },
        consecutive_failures=consecutive_failures,
        last_online=last_online,
    )


async def _setup_integration(
    hass: HomeAssistant, default_options: dict[str, Any], result: CheckOnlineResult
) -> MockConfigEntry:
    """Set up the integration with a mock coordinator."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=default_options)
    entry.add_to_hass(hass)

    mock_coordinator = MagicMock(spec=CheckOnlineCoordinator)
    mock_coordinator.data = result
    mock_coordinator.last_update_success = True
    mock_coordinator.config_entry = entry

    entry.runtime_data = mock_coordinator

    with patch(
        "custom_components.check_online.sensor.CheckOnlineCoordinator",
        return_value=mock_coordinator,
    ):
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        await hass.async_block_till_done()

    return entry


class TestRttSensors:
    """Tests for round-trip time sensors."""

    async def test_all_disabled_by_default(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        for i in range(1, 4):
            entity = ent_reg.async_get(f"sensor.check_online_target_{i}_rtt")
            assert entity is not None
            assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    async def test_entity_category_diagnostic(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_target_1_rtt")
        assert entity is not None
        assert entity.entity_category == EntityCategory.DIAGNOSTIC


class TestLastOnlineSensor:
    """Tests for the last_online timestamp sensor."""

    async def test_disabled_by_default(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_last_online")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION


class TestConsecutiveFailuresSensor:
    """Tests for the consecutive_failures sensor."""

    async def test_disabled_by_default(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_consecutive_failures")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sensor.py -v`
Expected: FAIL — sensor module does not exist yet.

- [ ] **Step 3: Implement `custom_components/check_online/sensor.py`**

```python
"""Sensor platform for the Check Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import CONF_TARGET_1, CONF_TARGET_2, CONF_TARGET_3
from .coordinator import CheckOnlineCoordinator, CheckOnlineResult
from .entity import CheckOnlineEntity


@dataclass(frozen=True, kw_only=True)
class CheckOnlineSensorDescription(SensorEntityDescription):
    """Describe a Check Online sensor."""

    value_fn: Callable[[CheckOnlineResult], StateType | datetime]


TARGET_RTT_SENSORS: list[tuple[str, str]] = [
    (CONF_TARGET_1, "target_1_rtt"),
    (CONF_TARGET_2, "target_2_rtt"),
    (CONF_TARGET_3, "target_3_rtt"),
]


def _make_rtt_description(target: str, key: str) -> CheckOnlineSensorDescription:
    return CheckOnlineSensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement="ms",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data, t=target: (
            data.target_results[t].rtt if t in data.target_results else None
        ),
    )


LAST_ONLINE_SENSOR = CheckOnlineSensorDescription(
    key="last_online",
    translation_key="last_online",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=lambda data: data.last_online,
)

CONSECUTIVE_FAILURES_SENSOR = CheckOnlineSensorDescription(
    key="consecutive_failures",
    translation_key="consecutive_failures",
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=lambda data: data.consecutive_failures,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Check Online sensors."""
    coordinator: CheckOnlineCoordinator = entry.runtime_data

    descriptions: list[CheckOnlineSensorDescription] = []
    for conf_key, entity_key in TARGET_RTT_SENSORS:
        target = entry.options[conf_key]
        descriptions.append(_make_rtt_description(target, entity_key))

    descriptions.append(LAST_ONLINE_SENSOR)
    descriptions.append(CONSECUTIVE_FAILURES_SENSOR)

    async_add_entities(
        CheckOnlineSensor(coordinator, entry.entry_id, desc)
        for desc in descriptions
    )


class CheckOnlineSensor(CheckOnlineEntity, SensorEntity):
    """Sensor for Check Online."""

    entity_description: CheckOnlineSensorDescription

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        description: CheckOnlineSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sensor.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/check_online/sensor.py tests/test_sensor.py
git commit -m "Add sensor entities: per-target RTT, last online, consecutive failures"
```

---

### Task 8: Config Flow

**Files:**
- Create: `custom_components/check_online/config_flow.py`
- Create: `tests/test_config_flow.py`

- [ ] **Step 1: Write failing tests for config flow**

Create `tests/test_config_flow.py`:

```python
"""Tests for check_online config flow."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import (
    CONF_OFFLINE_INTERVAL,
    CONF_PING_TIMEOUT,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    DEFAULT_OFFLINE_INTERVAL,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_1,
    DEFAULT_TARGET_2,
    DEFAULT_TARGET_3,
    DOMAIN,
)


class TestConfigFlowUser:
    """Tests for the user config flow step."""

    async def test_show_form(self, hass: HomeAssistant) -> None:
        """Test that the form is shown with defaults."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_create_entry_with_defaults(self, hass: HomeAssistant) -> None:
        """Test creating an entry with default values."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_TARGET_1: DEFAULT_TARGET_1,
                CONF_TARGET_2: DEFAULT_TARGET_2,
                CONF_TARGET_3: DEFAULT_TARGET_3,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Check Online"
        assert result["options"][CONF_TARGET_1] == DEFAULT_TARGET_1
        assert result["options"][CONF_TARGET_2] == DEFAULT_TARGET_2
        assert result["options"][CONF_TARGET_3] == DEFAULT_TARGET_3
        assert result["options"][CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL

    async def test_create_entry_with_custom_targets(self, hass: HomeAssistant) -> None:
        """Test creating an entry with custom targets."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_TARGET_1: "192.168.1.1",
                CONF_TARGET_2: "10.0.0.1",
                CONF_TARGET_3: "example.com",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["options"][CONF_TARGET_1] == "192.168.1.1"
        assert result["options"][CONF_TARGET_2] == "10.0.0.1"
        assert result["options"][CONF_TARGET_3] == "example.com"


class TestOptionsFlow:
    """Tests for the options flow."""

    async def test_show_form_with_current_values(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={}, options=default_options)
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_update_options(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={}, options=default_options)
        entry.add_to_hass(hass)

        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_TARGET_1: "192.168.1.1",
                CONF_TARGET_2: "10.0.0.1",
                CONF_TARGET_3: "example.com",
                CONF_SCAN_INTERVAL: 120,
                CONF_OFFLINE_INTERVAL: 60,
                CONF_RETRY_DELAY: 10,
                CONF_RETRY_COUNT: 3,
                CONF_PING_TIMEOUT: 1000,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_TARGET_1] == "192.168.1.1"
        assert result["data"][CONF_SCAN_INTERVAL] == 120
        assert result["data"][CONF_PING_TIMEOUT] == 1000


class TestImportFlow:
    """Tests for YAML import."""

    async def test_import_creates_entry(self, hass: HomeAssistant) -> None:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_TARGET_1: "8.8.8.8",
                CONF_TARGET_2: "1.1.1.1",
                CONF_TARGET_3: "9.9.9.9",
                CONF_SCAN_INTERVAL: 60,
                CONF_OFFLINE_INTERVAL: 30,
                CONF_RETRY_DELAY: 5,
                CONF_RETRY_COUNT: 2,
                CONF_PING_TIMEOUT: 500,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

    async def test_import_aborts_if_already_configured(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={}, options=default_options)
        entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_TARGET_1: "8.8.8.8",
                CONF_TARGET_2: "1.1.1.1",
                CONF_TARGET_3: "9.9.9.9",
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_flow.py -v`
Expected: FAIL — config_flow module does not exist yet.

- [ ] **Step 3: Implement `custom_components/check_online/config_flow.py`**

```python
"""Config flow for the Check Online integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_OFFLINE_INTERVAL,
    CONF_PING_TIMEOUT,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    DEFAULT_OFFLINE_INTERVAL,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_1,
    DEFAULT_TARGET_2,
    DEFAULT_TARGET_3,
    DOMAIN,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TARGET_1, default=DEFAULT_TARGET_1): str,
        vol.Required(CONF_TARGET_2, default=DEFAULT_TARGET_2): str,
        vol.Required(CONF_TARGET_3, default=DEFAULT_TARGET_3): str,
    }
)


class CheckOnlineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Check Online."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Check Online",
                data={},
                options={
                    CONF_TARGET_1: user_input[CONF_TARGET_1],
                    CONF_TARGET_2: user_input[CONF_TARGET_2],
                    CONF_TARGET_3: user_input[CONF_TARGET_3],
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    CONF_OFFLINE_INTERVAL: DEFAULT_OFFLINE_INTERVAL,
                    CONF_RETRY_DELAY: DEFAULT_RETRY_DELAY,
                    CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
                    CONF_PING_TIMEOUT: DEFAULT_PING_TIMEOUT,
                },
            )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle import from YAML."""
        self._async_abort_entries_match()

        return self.async_create_entry(
            title="Check Online",
            data={},
            options={
                CONF_TARGET_1: import_data[CONF_TARGET_1],
                CONF_TARGET_2: import_data[CONF_TARGET_2],
                CONF_TARGET_3: import_data[CONF_TARGET_3],
                CONF_SCAN_INTERVAL: import_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                CONF_OFFLINE_INTERVAL: import_data.get(CONF_OFFLINE_INTERVAL, DEFAULT_OFFLINE_INTERVAL),
                CONF_RETRY_DELAY: import_data.get(CONF_RETRY_DELAY, DEFAULT_RETRY_DELAY),
                CONF_RETRY_COUNT: import_data.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT),
                CONF_PING_TIMEOUT: import_data.get(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> CheckOnlineOptionsFlow:
        """Return the options flow handler."""
        return CheckOnlineOptionsFlow()


class CheckOnlineOptionsFlow(OptionsFlow):
    """Handle options for Check Online."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        options_schema = vol.Schema(
            {
                vol.Required(CONF_TARGET_1, default=current.get(CONF_TARGET_1, DEFAULT_TARGET_1)): str,
                vol.Required(CONF_TARGET_2, default=current.get(CONF_TARGET_2, DEFAULT_TARGET_2)): str,
                vol.Required(CONF_TARGET_3, default=current.get(CONF_TARGET_3, DEFAULT_TARGET_3)): str,
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=10)),
                vol.Required(
                    CONF_OFFLINE_INTERVAL,
                    default=current.get(CONF_OFFLINE_INTERVAL, DEFAULT_OFFLINE_INTERVAL),
                ): vol.All(int, vol.Range(min=5)),
                vol.Required(
                    CONF_RETRY_DELAY,
                    default=current.get(CONF_RETRY_DELAY, DEFAULT_RETRY_DELAY),
                ): vol.All(int, vol.Range(min=1)),
                vol.Required(
                    CONF_RETRY_COUNT,
                    default=current.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT),
                ): vol.All(int, vol.Range(min=0, max=10)),
                vol.Required(
                    CONF_PING_TIMEOUT,
                    default=current.get(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT),
                ): vol.All(int, vol.Range(min=100, max=5000)),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_flow.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/check_online/config_flow.py tests/test_config_flow.py
git commit -m "Add config flow with user setup, options flow, and YAML import"
```

---

### Task 9: Integration Setup (`__init__.py`)

**Files:**
- Modify: `custom_components/check_online/__init__.py`

- [ ] **Step 1: Implement the full `__init__.py`**

Replace the minimal `__init__.py` with the complete version:

```python
"""The Check Online integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_OFFLINE_INTERVAL,
    CONF_PING_TIMEOUT,
    CONF_RETRY_COUNT,
    CONF_RETRY_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_TARGET_1,
    CONF_TARGET_2,
    CONF_TARGET_3,
    CONF_TARGETS,
    DEFAULT_OFFLINE_INTERVAL,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_RETRY_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TARGET_1,
    DEFAULT_TARGET_2,
    DEFAULT_TARGET_3,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CheckOnlineCoordinator
from .helpers import DnsResolver, PingHelper, PingMode, detect_ping_mode

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_TARGETS,
                    default=[DEFAULT_TARGET_1, DEFAULT_TARGET_2, DEFAULT_TARGET_3],
                ): vol.All(cv.ensure_list, [str], vol.Length(min=3, max=3)),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    int, vol.Range(min=10)
                ),
                vol.Optional(CONF_OFFLINE_INTERVAL, default=DEFAULT_OFFLINE_INTERVAL): vol.All(
                    int, vol.Range(min=5)
                ),
                vol.Optional(CONF_RETRY_DELAY, default=DEFAULT_RETRY_DELAY): vol.All(
                    int, vol.Range(min=1)
                ),
                vol.Optional(CONF_RETRY_COUNT, default=DEFAULT_RETRY_COUNT): vol.All(
                    int, vol.Range(min=0, max=10)
                ),
                vol.Optional(CONF_PING_TIMEOUT, default=DEFAULT_PING_TIMEOUT): vol.All(
                    int, vol.Range(min=100, max=5000)
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

DATA_PING_MODE = "ping_mode"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up Check Online from YAML configuration."""
    if DOMAIN not in config:
        return True

    yaml_config = config[DOMAIN]
    targets = yaml_config[CONF_TARGETS]

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_TARGET_1: targets[0],
                CONF_TARGET_2: targets[1],
                CONF_TARGET_3: targets[2],
                CONF_SCAN_INTERVAL: yaml_config[CONF_SCAN_INTERVAL],
                CONF_OFFLINE_INTERVAL: yaml_config[CONF_OFFLINE_INTERVAL],
                CONF_RETRY_DELAY: yaml_config[CONF_RETRY_DELAY],
                CONF_RETRY_COUNT: yaml_config[CONF_RETRY_COUNT],
                CONF_PING_TIMEOUT: yaml_config[CONF_PING_TIMEOUT],
            },
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Check Online from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Detect ping mode once, cache for all entries
    if DATA_PING_MODE not in hass.data[DOMAIN]:
        ping_mode = await detect_ping_mode()
        hass.data[DOMAIN][DATA_PING_MODE] = ping_mode
        _LOGGER.info("Detected ping mode: %s", ping_mode.value)
    else:
        ping_mode = hass.data[DOMAIN][DATA_PING_MODE]

    timeout_ms = entry.options.get(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT)
    ping_helper = PingHelper(ping_mode, timeout_ms=timeout_ms)
    dns_resolver = DnsResolver(hass)

    coordinator = CheckOnlineCoordinator(
        hass=hass,
        config_entry=entry,
        ping_helper=ping_helper,
        dns_resolver=dns_resolver,
    )

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- [ ] **Step 2: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add custom_components/check_online/__init__.py
git commit -m "Complete integration setup with privilege detection, YAML import, and reload"
```

---

### Task 10: Lint, Type Check, and Final Verification

**Files:**
- Potentially fix: any files flagged by ruff or mypy

- [ ] **Step 1: Run ruff format**

```bash
ruff format custom_components/ tests/
```

- [ ] **Step 2: Run ruff check and fix**

```bash
ruff check custom_components/ tests/ --fix
```

Fix any remaining issues manually.

- [ ] **Step 3: Run mypy**

```bash
mypy custom_components/
```

Fix any type errors. Common issues to expect:
- Missing type stubs for HA (handled by `ignore_missing_imports`)
- Lambda type inference in entity descriptions

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Run tox to verify all environments**

```bash
tox
```

Expected: `lint`, `typecheck`, and `test` all pass.

- [ ] **Step 6: Commit any fixes**

```bash
git add -u
git commit -m "Fix lint and type check issues"
```
