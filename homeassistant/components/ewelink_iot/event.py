"""Event platform for eWeLink IoT integration."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import EVENT_ENTITY_TYPE, PLATFORM, get_uiid_instance
from .utils import gen_event_callback_key


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up eWeLink button event from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkEvent] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and uiid_instance.platform_config is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            event_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.EVENT
            ]
            for event_config in event_config_list:
                ewelink_event_entity = None
                event_entity_type = event_config.get("type")
                if event_entity_type == EVENT_ENTITY_TYPE.BUTTON:
                    ewelink_event_entity = EWeLinkButtonEvent(
                        coordinator, device_id, event_config.get("config")
                    )

                if ewelink_event_entity is not None:
                    entities.append(ewelink_event_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkEvent(EWeLinkEntity, EventEntity):
    """Representation of an ewelink event."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self.uiid_instance = get_uiid_instance(self.ewelink_device.uiid)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=self.ewelink_device.device_name,
            manufacturer=self.ewelink_device.manufacturer,
            model=self.ewelink_device.model,
            serial_number=device_id,
        )

    @property
    def ewelink_device(self):
        """Get EWeLinkDevice instance."""
        return self.coordinator.data.get(self.device_id)


class EWeLinkButtonEvent(EWeLinkEvent):
    """Representation of an ewelink button."""

    _attr_device_class = EventDeviceClass.BUTTON

    def __init__(
        self, coordinator: EWeLinkDataCoordinator, device_id: str, config=None
    ) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self.config = config
        self._attr_unique_id = f"{DOMAIN}_{self.device_id}_{self.outlet}_button_event"
        self._last_event = self.native_event

    @property
    def outlet(self) -> int:
        """Button outlet."""
        config = self.config
        if config is not None:
            return config.get("outlet") if type(config.get("outlet")) is int else 0
        return 0

    @property
    def event_types(self):
        """A list of possible event types this entity can fire."""
        event_types = self.uiid_instance.event_types
        return event_types if isinstance(event_types, list) is not None else []

    @property
    def native_event(self) -> str | None:
        """Return the last event type."""
        outlet_state = self.uiid_instance.get_outlet_state(self.ewelink_device.device)
        value = None
        if outlet_state.get("outlet") == self.outlet:
            value = outlet_state.get("event_type")
        self._last_event = value
        return value

    @callback
    def handle_trigger_event(self, outlet, key, event_attributes=None):
        """Trigger event."""
        event_type = self.uiid_instance.key_2_event_type(key)
        if outlet == self.outlet and event_type in self.event_types:
            self._trigger_event(event_type, event_attributes)

    async def async_added_to_hass(self) -> None:
        """Register callbacks with your event entity added."""
        await super().async_added_to_hass()
        key = gen_event_callback_key(self.device_id, self.outlet)
        self.coordinator.add_event_handler(key, self.handle_trigger_event)

    async def async_will_remove_from_hass(self):
        """Unregister callbacks when delete event entity."""
        await super().async_will_remove_from_hass()
        key = gen_event_callback_key(self.device_id, self.outlet)
        self.coordinator.remove_event_handler(key)
