"""Switch platform for eWeLink IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from . import EWeLinkConfigEntry
from .api import EWeLinkApiError, EWeLinkDevice
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .const import DOMAIN, COORDINATOR
from .uiid.switch import (
    MULTIPLE_SINGLE_PROTOCOL_UIIDS,
    SwitchCoordinator,
    SINGLE_PROTOCOL_UIIDS,
    SWITCH_UIIDS,
    OFF,
    ON,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EWeLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eWeLink switches from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkSwitch] = []
    switch_and_toggle_device_dict = {
        device_id: device
        for device_id, device in coordinator.data.items()
        if device.uiid in SWITCH_UIIDS
    }

    for device_id, device in switch_and_toggle_device_dict.items():
        uiid = device.uiid
        if uiid in [*MULTIPLE_SINGLE_PROTOCOL_UIIDS, *SINGLE_PROTOCOL_UIIDS]:
            ewelink_switch = EWeLinkSwitch(
                coordinator=coordinator, device_id=device_id, device=device
            )
            entities.append(ewelink_switch)

    async_add_entities(entities)


class EWeLinkSwitch(EWeLinkEntity, SwitchEntity):
    """Representation of an eWeLink switch."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EWeLinkDataCoordinator, device_id: str, device: EWeLinkDevice
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)

        self._device = device
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.device_name,
            manufacturer=device.manufacturer,
            model=device.model,
            serial_number=device_id,
        )
        self._attr_unique_id = f"ewelink_{device_id}_switch"
        self._attr_name = None  # Use device name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if not self._device:
            return False
        return SwitchCoordinator.get_switch_state(self._device) == ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_switch_state(False)

    async def _async_set_switch_state(self, state: bool) -> None:
        """Set switch state."""
        if not self._device:
            return

        try:
            self.async_write_ha_state()

        except EWeLinkApiError as err:
            self._attr_available = False
            self.async_write_ha_state()
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()
