"""Config flow for the Check Online integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_import(self, import_data: dict[str, Any]) -> ConfigFlowResult:
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
    def async_get_options_flow(config_entry: ConfigEntry) -> CheckOnlineOptionsFlow:
        """Return the options flow handler."""
        return CheckOnlineOptionsFlow()


class CheckOnlineOptionsFlow(OptionsFlow):
    """Handle options for Check Online."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TARGET_1,
                    default=current.get(CONF_TARGET_1, DEFAULT_TARGET_1),
                ): str,
                vol.Required(
                    CONF_TARGET_2,
                    default=current.get(CONF_TARGET_2, DEFAULT_TARGET_2),
                ): str,
                vol.Required(
                    CONF_TARGET_3,
                    default=current.get(CONF_TARGET_3, DEFAULT_TARGET_3),
                ): str,
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
