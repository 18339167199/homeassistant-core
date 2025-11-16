"""Switch platform for eWeLink IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EWeLinkConfigEntry
from .api import EWeLinkApiError
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EWeLinkConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eWeLink switches from a config entry."""
    coordinator = entry.runtime_data

    entities: list[EWeLinkSwitch] = []

    # for device_id, device in coordinator.data.items():
    #     # Get switch count from device params
    #     switches = device.params.get("switches", [])

    #     if switches:
    #         # Multi-channel switch
    #         for idx, switch_data in enumerate(switches):
    #             entities.append(
    #                 EWeLinkSwitch(
    #                     coordinator=coordinator,
    #                     device_id=device_id,
    #                     channel=idx,
    #                 )
    #             )
    #     else:
    #         # Single switch
    #         if "switch" in device.params:
    #             entities.append(
    #                 EWeLinkSwitch(
    #                     coordinator=coordinator,
    #                     device_id=device_id,
    #                     channel=None,
    #                 )
    #             )

    async_add_entities(entities)


class EWeLinkSwitch(EWeLinkEntity, SwitchEntity):
    """Representation of an eWeLink switch."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EWeLinkDataCoordinator,
        device_id: str,
        channel: int | None,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)

        self._channel = channel

        # Set unique ID
        if channel is not None:
            self._attr_unique_id = f"{device_id}_switch_{channel}"
            self._attr_name = f"Channel {channel + 1}"
            self._attr_translation_key = "switch_channel"
            self._attr_translation_placeholders = {"channel": str(channel + 1)}
        else:
            self._attr_unique_id = f"{device_id}_switch"
            self._attr_name = None  # Use device name

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        device = self.coordinator.data.get(self._device_id)
        if not device:
            return False

        if self._channel is not None:
            # Multi-channel switch
            switches = device.params.get("switches", [])
            if self._channel < len(switches):
                return switches[self._channel].get("switch") == "on"
        else:
            # Single switch
            return device.params.get("switch") == "on"

        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_switch_state(False)

    async def _async_set_switch_state(self, state: bool) -> None:
        """Set switch state."""
        device = self.coordinator.data.get(self._device_id)
        if not device:
            return

        state_str = "on" if state else "off"

        try:
            if self._channel is not None:
                # Multi-channel switch
                switches = device.params.get("switches", []).copy()
                if self._channel < len(switches):
                    switches[self._channel]["switch"] = state_str

                    await self.coordinator.api_client.set_device_status(
                        self._device_id,
                        {"switches": switches},
                    )
            else:
                # Single switch
                await self.coordinator.api_client.set_device_status(
                    self._device_id,
                    {"switch": state_str},
                )

            # Update local state immediately
            if self._channel is not None:
                device.params.setdefault("switches", [])[self._channel]["switch"] = (
                    state_str
                )
            else:
                device.params["switch"] = state_str

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

        # Register callback for WebSocket updates
        self.coordinator.register_device_callback(
            self._device_id, self._handle_coordinator_update
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        await super().async_will_remove_from_hass()

        # Unregister callback
        self.coordinator.unregister_device_callback(self._device_id)
