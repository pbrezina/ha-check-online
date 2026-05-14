"""Tests for check_online config flow."""

from __future__ import annotations

from typing import Any

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


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations in all tests in this module."""


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
        assert result["reason"] == "single_instance_allowed"
