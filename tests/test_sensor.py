"""Tests for check_online sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.check_online.const import DOMAIN
from custom_components.check_online.coordinator import (
    CheckOnlineCoordinator,
    CheckOnlineResult,
    TargetResult,
)


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations in all tests in this module."""


def _make_result(
    is_online: bool = True,
    rtt_1: float | None = 10.0,
    rtt_2: float | None = 15.0,
    rtt_3: float | None = 20.0,
    consecutive_failures: int = 0,
    last_online: datetime | None = None,
    last_offline: datetime | None = None,
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
        last_offline=last_offline,
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

    async def mock_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        entry.runtime_data = mock_coordinator
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        return True

    with patch(
        "custom_components.check_online.async_setup_entry",
        side_effect=mock_setup_entry,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


class TestRttSensors:
    """Tests for round-trip time sensors."""

    async def test_all_disabled_by_default(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        for i in range(1, 4):
            entity = ent_reg.async_get(f"sensor.check_online_target_{i}_rtt")
            assert entity is not None
            assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    async def test_entity_category_diagnostic(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_target_1_rtt")
        assert entity is not None
        assert entity.entity_category == EntityCategory.DIAGNOSTIC


class TestLastOnlineSensor:
    """Tests for the last_online timestamp sensor."""

    async def test_disabled_by_default(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_last_online")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION


class TestLastOfflineSensor:
    """Tests for the last_offline timestamp sensor."""

    async def test_disabled_by_default(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_last_offline")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION


class TestConsecutiveFailuresSensor:
    """Tests for the consecutive_failures sensor."""

    async def test_disabled_by_default(self, hass: HomeAssistant, default_options: dict[str, Any]) -> None:
        result = _make_result()
        await _setup_integration(hass, default_options, result)

        ent_reg = er.async_get(hass)
        entity = ent_reg.async_get("sensor.check_online_consecutive_failures")
        assert entity is not None
        assert entity.disabled_by == er.RegistryEntryDisabler.INTEGRATION
