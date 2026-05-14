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
