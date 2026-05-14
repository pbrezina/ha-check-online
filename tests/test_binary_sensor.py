"""Tests for check_online binary sensors."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
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


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations in all tests in this module."""


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

    async def mock_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry
    ) -> bool:
        entry.runtime_data = mock_coordinator
        await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor"])
        return True

    with patch(
        "custom_components.check_online.async_setup_entry",
        side_effect=mock_setup_entry,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
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
