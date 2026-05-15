"""Tests for CheckOnlineCoordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import (
    CONF_OFFLINE_INTERVAL,
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

    async def test_stays_online_when_all_respond(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0

    async def test_stays_online_when_one_responds(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_one_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True

    async def test_retries_before_going_offline(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """All pings fail -> should retry retry_count times before going offline."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.consecutive_failures == 1
        assert coordinator._ping_all_targets.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(default_options[CONF_RETRY_DELAY])

    async def test_retry_succeeds_stays_online(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """First ping fails, retry succeeds -> stay online."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(side_effect=[_all_dead(default_options), _all_alive(default_options)])
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0

    async def test_interval_changes_to_offline(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.update_interval == timedelta(seconds=default_options[CONF_OFFLINE_INTERVAL])


class TestOfflineState:
    """Tests for behavior when coordinator is in OFFLINE state."""

    async def _go_offline(
        self,
        coordinator: CheckOnlineCoordinator,
        options: dict[str, Any],
    ) -> None:
        """Helper: drive coordinator to OFFLINE state."""
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False

    async def test_goes_online_on_success(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.consecutive_failures == 0
        assert coordinator.update_interval == timedelta(seconds=default_options[CONF_SCAN_INTERVAL])

    async def test_stays_offline_on_failure(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)
        failures_after_first_offline = coordinator.data.consecutive_failures
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.consecutive_failures == failures_after_first_offline + 1

    async def test_one_alive_enough_to_go_online(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        await self._go_offline(coordinator, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_one_alive(default_options))
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

    async def test_dns_failure_for_one_target(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
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

    async def test_set_on_first_successful_ping(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """last_online should be set on the first successful ping after startup."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.last_online is not None

    async def test_set_on_first_successful_retry(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """last_online should be set even if only a retry succeeds on the first poll."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(side_effect=[_all_dead(default_options), _all_alive(default_options)])
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.last_online is not None

    async def test_set_on_offline_to_online_transition(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """last_online should be set when transitioning from offline to online."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # Go offline
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.last_online is None

        # Go back online
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.last_online is not None

    async def test_updated_on_offline_to_online_after_initial(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """last_online should be updated on offline->online even if already set by first ping."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # First successful ping sets last_online
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        initial_last_online = coordinator.data.last_online
        assert initial_last_online is not None

        # Go offline
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False

        # Go back online -- last_online should be updated
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.last_online is not None
        assert coordinator.data.last_online >= initial_last_online

    async def test_preserved_when_offline(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # Go offline then online to set last_online
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        last_online = coordinator.data.last_online
        assert last_online is not None

        # Go offline again
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.last_online == last_online


class TestLastOffline:
    """Tests for last_offline timestamp tracking."""

    async def test_none_when_online(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """last_offline should be None when the system has never gone offline."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.last_offline is None

    async def test_set_when_going_offline(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """last_offline should be set when the system transitions to offline."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.last_offline is not None

    async def test_preserved_when_back_online(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """last_offline should be preserved when the system goes back online."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # Go offline
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        last_offline = coordinator.data.last_offline
        assert last_offline is not None

        # Go back online
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True
        assert coordinator.data.last_offline == last_offline

    async def test_updated_on_new_offline_transition(
        self, hass: HomeAssistant, default_options: dict[str, Any]
    ) -> None:
        """last_offline should update when going offline again after being online."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # Go offline
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        first_offline = coordinator.data.last_offline
        assert first_offline is not None

        # Go back online
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        assert coordinator.data.is_online is True

        # Go offline again
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        assert coordinator.data.is_online is False
        assert coordinator.data.last_offline is not None
        assert coordinator.data.last_offline >= first_offline


class TestTimestampCaching:
    """Tests that timestamps survive coordinator recreation (integration reload)."""

    async def test_last_online_survives_reload(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """A new coordinator should pick up last_online from hass.data cache."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        cached_last_online = coordinator.data.last_online
        assert cached_last_online is not None

        # Simulate reload: create a new coordinator on the same hass instance
        coordinator2, _, _ = _make_coordinator(hass, default_options)
        coordinator2._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator2.async_refresh()
        assert coordinator2.data.last_online == cached_last_online

    async def test_last_offline_survives_reload(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """A new coordinator should pick up last_offline from hass.data cache."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        cached_last_offline = coordinator.data.last_offline
        assert cached_last_offline is not None

        # Simulate reload: create a new coordinator on the same hass instance
        coordinator2, _, _ = _make_coordinator(hass, default_options)
        coordinator2._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator2.async_refresh()
        assert coordinator2.data.last_offline == cached_last_offline

    async def test_both_survive_reload(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        """Both timestamps should survive a coordinator recreation."""
        coordinator, _, _ = _make_coordinator(hass, default_options)
        # Go online then offline to set both timestamps
        coordinator._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator.async_refresh()
        coordinator._ping_all_targets = AsyncMock(return_value=_all_dead(default_options))
        with patch(
            "custom_components.check_online.coordinator.asyncio.sleep",
            new_callable=AsyncMock,
        ):
            await coordinator.async_refresh()
        cached_last_online = coordinator.data.last_online
        cached_last_offline = coordinator.data.last_offline
        assert cached_last_online is not None
        assert cached_last_offline is not None

        # Simulate reload
        coordinator2, _, _ = _make_coordinator(hass, default_options)
        coordinator2._ping_all_targets = AsyncMock(return_value=_all_alive(default_options))
        await coordinator2.async_refresh()
        assert coordinator2.data.last_online == cached_last_online
        assert coordinator2.data.last_offline == cached_last_offline
