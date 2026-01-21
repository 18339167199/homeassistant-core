"""Light platform for eWeLink IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    DEFAULT_MAX_KELVIN,
    DEFAULT_MIN_KELVIN,
    ColorMode,
    LightEntity,
)
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
    entities: list[EWeLinkLight] = []

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
                ewelink_light_entity = EWeLinkLight(
                    coordinator, device_id, light_config.get("config")
                )
                entities.append(ewelink_light_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkLight(EWeLinkEntity, LightEntity):
    """Representation of an ewelink event."""

    _attr_has_entity_name = True

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
        if hasattr(self.uiid_instance, "supported_color_modes"):
            return self.uiid_instance.supported_color_modes
        return set()

    @property
    def color_mode(self) -> ColorMode | None:
        """Light color mode."""
        return self.uiid_instance.get_color_mode(self.ewelink_device.device)

    @property
    def brightness(self) -> int | None:
        """Light brightness, range: 1 ~ 255."""
        return self.uiid_instance.get_brightess(self.ewelink_device.device)

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Light rgb color."""
        return self.uiid_instance.get_color_rgb(self.ewelink_device.device)

    @property
    def color_temp_kelvin(self):
        """Light color temp."""
        return self.uiid_instance.get_color_temp_kelvin(self.ewelink_device.device)

    @property
    def max_color_temp_kelvin(self):
        """Return the max color temp kelvin."""
        if hasattr(self.uiid_instance, "max_color_temp_kelvin"):
            return self.uiid_instance.max_color_temp_kelvin
        return DEFAULT_MAX_KELVIN

    @property
    def min_color_temp_kelvin(self):
        """Return the min color temp kelvin."""
        if hasattr(self.uiid_instance, "min_color_temp_kelvin"):
            return self.uiid_instance.min_color_temp_kelvin
        return DEFAULT_MIN_KELVIN

    @property
    def is_on(self) -> bool:
        """Light is on."""
        return self.uiid_instance.get_switch_value(self.ewelink_device.device)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # kwargs:
        # control brightness: {'brightness': 134}
        # control color rgb: {'rgb_color': (113, 255, 134), 'brightness': 173}
        # control color temp: {'color_temp': 294, 'color_temp_kelvin': 3392}
        control_params = None
        if "color_temp_kelvin" in kwargs:
            color_temp_kelvin = kwargs.get("color_temp_kelvin")
            control_params = self.uiid_instance.gen_control_color_temp_params(
                self.ewelink_device.device, color_temp_kelvin
            )
        elif "rgb_color" in kwargs:
            rgb_color = kwargs.get("rgb_color")
            control_params = self.uiid_instance.gen_control_color_rgb_params(
                self.ewelink_device.device, rgb_color
            )
        elif "brightness" in kwargs:
            brightness = kwargs.get("brightness")
            control_params = self.uiid_instance.gen_control_brightness_params(
                self.ewelink_device.device, brightness
            )
        else:
            control_params = self.uiid_instance.gen_control_switch_params(True)

        result = await self.coordinator.control_device(
            self.ewelink_device, control_params
        )
        if result is not None and result.get("error") == 0:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        result = await self.coordinator.control_device(
            self.ewelink_device, self.uiid_instance.gen_control_switch_params(False)
        )
        if result is not None and result.get("error") == 0:
            self.async_write_ha_state()
