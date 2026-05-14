"""Config flow for the Check Online integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class CheckOnlineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Check Online."""

    VERSION = 1
