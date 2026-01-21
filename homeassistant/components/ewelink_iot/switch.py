"""Switch platform for eWeLink IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import PLATFORM, get_uiid_instance


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up eWeLink switches from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkSwitch] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and uiid_instance.platform_config is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            switch_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.SWITCH
            ]
            for switch_config in switch_config_list:
                ewelink_switch_entity = EWeLinkSwitch(
                    coordinator, device_id, switch_config
                )
                entities.append(ewelink_switch_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkSwitch(EWeLinkEntity, SwitchEntity):
    """Representation of an eWeLink switch."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: EWeLinkDataCoordinator, device_id: str, config=None
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)
        self.config = config
        self._attr_unique_id = f"ewelink_lot_{device_id}_switch"
        self._attr_name = None  # Use device name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        if not self.ewelink_device or not self.uiid_instance:
            return False
        return self.uiid_instance.get_switch_value(self.ewelink_device.device)

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
        params = self.uiid_instance.gen_control_switch_params(is_on)
        result = await self.coordinator.control_device(self.ewelink_device, params)
        if result is not None and result.get("error") == 0:
            self._async_write_ha_state()
