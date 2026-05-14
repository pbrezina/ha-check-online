"""Sensor platform for the Check Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import CONF_TARGET_1, CONF_TARGET_2, CONF_TARGET_3
from .coordinator import CheckOnlineCoordinator, CheckOnlineResult
from .entity import CheckOnlineEntity


@dataclass(frozen=True, kw_only=True)
class CheckOnlineSensorDescription(SensorEntityDescription):
    """Describe a Check Online sensor."""

    value_fn: Callable[[CheckOnlineResult], StateType | datetime]


TARGET_RTT_SENSORS: list[tuple[str, str]] = [
    (CONF_TARGET_1, "target_1_rtt"),
    (CONF_TARGET_2, "target_2_rtt"),
    (CONF_TARGET_3, "target_3_rtt"),
]


def _make_rtt_value_fn(target: str) -> Callable[[CheckOnlineResult], StateType | datetime]:
    def _value_fn(data: CheckOnlineResult) -> StateType | datetime:
        return data.target_results[target].rtt if target in data.target_results else None

    return _value_fn


def _make_rtt_description(target: str, key: str) -> CheckOnlineSensorDescription:
    return CheckOnlineSensorDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement="ms",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_make_rtt_value_fn(target),
    )


LAST_ONLINE_SENSOR = CheckOnlineSensorDescription(
    key="last_online",
    translation_key="last_online",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=lambda data: data.last_online,
)

LAST_OFFLINE_SENSOR = CheckOnlineSensorDescription(
    key="last_offline",
    translation_key="last_offline",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=lambda data: data.last_offline,
)

CONSECUTIVE_FAILURES_SENSOR = CheckOnlineSensorDescription(
    key="consecutive_failures",
    translation_key="consecutive_failures",
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=lambda data: data.consecutive_failures,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Check Online sensors."""
    coordinator: CheckOnlineCoordinator = entry.runtime_data

    descriptions: list[CheckOnlineSensorDescription] = []
    for conf_key, entity_key in TARGET_RTT_SENSORS:
        target = entry.options[conf_key]
        descriptions.append(_make_rtt_description(target, entity_key))

    descriptions.append(LAST_ONLINE_SENSOR)
    descriptions.append(LAST_OFFLINE_SENSOR)
    descriptions.append(CONSECUTIVE_FAILURES_SENSOR)

    async_add_entities(CheckOnlineSensor(coordinator, entry.entry_id, desc) for desc in descriptions)


class CheckOnlineSensor(CheckOnlineEntity, SensorEntity):
    """Sensor for Check Online."""

    entity_description: CheckOnlineSensorDescription

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        description: CheckOnlineSensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
