"""Light platform for eWeLink IoT integration."""

from __future__ import annotations

from homeassistant.components.light import ColorMode, LightEntity
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
    """Set up eWeLink light from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinKLight] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            light_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.LIGHT
            ]
            for light_config in light_config_list:
                ewelink_light_entity = EWeLinKLight(
                    coordinator, device_id, light_config
                )
                entities.append(ewelink_light_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinKLight(EWeLinkEntity, LightEntity):
    """Representation of an ewelink event."""

    def __init__(
        self, coordinator: EWeLinkDataCoordinator, device_id: str, config=None
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_light"
        self.config = config

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Light support color mode."""
        if hasattr(self.config, "supported_color_modes") and isinstance(
            self.config.supported_color_modes, list
        ):
            return set(self.config.supported_color_modes)
        return set()

    @property
    def color_mode(self) -> ColorMode | None:
        """Light color mode."""
        return None

    @property
    def brightness(self) -> int | None:
        """Light brightness."""
        return 55

    @property
    def rgb_color(self):
        """Light rgb color."""
        return (100, 255, 200)  # r, g, b

    @property
    def color_temp_kelvin(self):
        """Light color temp."""
        return 4000

    @property
    def max_color_temp_kelvin(self):
        """Return the max color temp kelvin."""
        return 65535

    @property
    def min_color_temp_kelvin(self):
        """Return the min color temp kelvin."""
        return 2000

    @property
    def is_on(self) -> bool:
        """Light is on."""
        return self.uiid_instance.get_light_on_state(self.ewelink_device.device)

    def _control_switch(self, state: bool):
        """Control light switch."""
        pass

    def turn_on(self, **kwargs):
        """Turn the light on."""
        return super().turn_on(**kwargs)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        return super().turn_off(**kwargs)
