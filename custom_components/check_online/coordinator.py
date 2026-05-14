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
from .helpers import DnsResolver, PingHelper

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

        # All failed -- retry
        for _ in range(self._retry_count):
            await asyncio.sleep(self._retry_delay)
            target_results = await self._ping_all_targets()
            if self._any_alive(target_results):
                self._consecutive_failures = 0
                self._last_online = dt_util.utcnow()
                return self._make_result(True, target_results)

        # All retries exhausted -- go offline
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
