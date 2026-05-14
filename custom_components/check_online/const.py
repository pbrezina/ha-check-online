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
