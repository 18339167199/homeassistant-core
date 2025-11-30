"""Switch platform for eWeLink IoT integration."""

from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import SWITCH_UIIDS, get_device_coordinator
from .utils import get_device_uiid

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
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
        if uiid in SWITCH_UIIDS:
            ewelink_switch_entity = EWeLinkSwitch(
                coordinator=coordinator, device_id=device_id
            )
            entities.append(ewelink_switch_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkSwitch(EWeLinkEntity, SwitchEntity):
    """Representation of an eWeLink switch."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)

        self.device_id = device_id

        uiid = get_device_uiid(self.ewelink_device.device)
        self.device_coordinator = get_device_coordinator(uiid)

        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=self.ewelink_device.device_name,
            manufacturer=self.ewelink_device.manufacturer,
            model=self.ewelink_device.model,
            serial_number=device_id,
        )
        self._attr_unique_id = f"ewelink_{device_id}_switch"
        self._attr_name = None  # Use device name

    @property
    def ewelink_device(self):
        """Get EWeLinkDevice instance."""
        return self.coordinator.data.get(self.device_id)

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if not self.ewelink_device or not self.device_coordinator:
            return False
        return self.device_coordinator.get_switch_state(self.ewelink_device.device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_switch_state(False)

    async def _async_set_switch_state(self, is_on: bool) -> None:
        """Set switch state."""
        if not self.ewelink_device:
            return
        params = self.device_coordinator.gen_control_switch_params(is_on)
        _LOGGER.info(
            "[switch platform] control device_id: %s; params: %s",
            self.ewelink_device.device_id,
            json.dumps(params),
        )
        await self.coordinator.control_device(self.ewelink_device, params)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()
