"""The Check Online integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

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
from .helpers import DnsResolver, PingHelper, detect_ping_mode

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(
                    CONF_TARGETS,
                    default=[DEFAULT_TARGET_1, DEFAULT_TARGET_2, DEFAULT_TARGET_3],
                ): vol.All(cv.ensure_list, [str], vol.Length(min=3, max=3)),
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=10)),
                vol.Optional(CONF_OFFLINE_INTERVAL, default=DEFAULT_OFFLINE_INTERVAL): vol.All(int, vol.Range(min=5)),
                vol.Optional(CONF_RETRY_DELAY, default=DEFAULT_RETRY_DELAY): vol.All(int, vol.Range(min=1)),
                vol.Optional(CONF_RETRY_COUNT, default=DEFAULT_RETRY_COUNT): vol.All(int, vol.Range(min=0, max=10)),
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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok
