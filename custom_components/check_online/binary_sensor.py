"""Binary sensor platform for the Check Online integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TARGET_1, CONF_TARGET_2, CONF_TARGET_3
from .coordinator import CheckOnlineCoordinator, CheckOnlineResult
from .entity import CheckOnlineEntity


@dataclass(frozen=True, kw_only=True)
class CheckOnlineBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Check Online binary sensor."""

    value_fn: Callable[[CheckOnlineResult], bool]


MAIN_BINARY_SENSOR = CheckOnlineBinarySensorDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    value_fn=lambda data: data.is_online,
)

TARGET_SENSORS: list[tuple[str, str]] = [
    (CONF_TARGET_1, "target_1_status"),
    (CONF_TARGET_2, "target_2_status"),
    (CONF_TARGET_3, "target_3_status"),
]


def _make_target_value_fn(target: str) -> Callable[[CheckOnlineResult], bool]:
    def _value_fn(data: CheckOnlineResult) -> bool:
        return data.target_results[target].is_alive if target in data.target_results else False

    return _value_fn


def _make_target_description(target: str, key: str) -> CheckOnlineBinarySensorDescription:
    return CheckOnlineBinarySensorDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_make_target_value_fn(target),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Check Online binary sensors."""
    coordinator: CheckOnlineCoordinator = entry.runtime_data

    descriptions: list[CheckOnlineBinarySensorDescription] = [MAIN_BINARY_SENSOR]
    for conf_key, entity_key in TARGET_SENSORS:
        target = entry.options[conf_key]
        descriptions.append(_make_target_description(target, entity_key))

    async_add_entities(CheckOnlineBinarySensor(coordinator, entry.entry_id, desc) for desc in descriptions)


class CheckOnlineBinarySensor(CheckOnlineEntity, BinarySensorEntity):
    """Binary sensor for Check Online."""

    entity_description: CheckOnlineBinarySensorDescription

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        description: CheckOnlineBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, entry_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the network is online."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
