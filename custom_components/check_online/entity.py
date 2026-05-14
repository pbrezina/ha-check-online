"""Base entity for the Check Online integration."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CheckOnlineCoordinator


class CheckOnlineEntity(CoordinatorEntity[CheckOnlineCoordinator]):
    """Base class for Check Online entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CheckOnlineCoordinator,
        entry_id: str,
        key: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Check Online",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Write state only when it has actually changed."""
        if (current := self.hass.states.get(self.entity_id)) is not None:
            new_state = self.state
            if new_state is not None and current.state == str(new_state):
                return
        self.async_write_ha_state()
