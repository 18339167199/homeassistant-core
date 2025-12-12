"""Binary sensor Platform."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import BINARY_SENSOR_TYPE, PLATFORM, get_uiid_instance


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up eWeLink binary sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkBinarySensor] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and uiid_instance.platform_config is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            binary_sensor_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.BINARY_SENSOR
            ]
            for binary_sensor_config in binary_sensor_config_list:
                ewelink_binary_sensor_entity: EWeLinkBinarySensor | None = None
                binary_sensor_type = binary_sensor_config.get("type")
                if binary_sensor_type == BINARY_SENSOR_TYPE.DOOR:
                    ewelink_binary_sensor_entity = EWeLinkDoorBinarySensor(
                        coordinator, device_id
                    )
                elif binary_sensor_type == BINARY_SENSOR_TYPE.HUMAN:
                    ewelink_binary_sensor_entity = EWeLinkHumanBinarySensor(
                        coordinator, device_id
                    )

                if ewelink_binary_sensor_entity is not None:
                    entities.append(ewelink_binary_sensor_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkBinarySensor(EWeLinkEntity, BinarySensorEntity):
    """Representation of an EWeLink binary sensor."""

    _attr_has_entity_name = True


class EWeLinkDoorBinarySensor(EWeLinkBinarySensor):
    """EWeLink door sensor."""

    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"ewelink_lot_{device_id}_door_binary_sensor"

    @property
    def is_on(self) -> bool | None:
        """Get door binary sensor state."""
        return self.uiid_instance.get_door_lock_value(self.ewelink_device.device)


class EWeLinkHumanBinarySensor(EWeLinkBinarySensor):
    """EWeLink human binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_human_binary_sensor"

    @property
    def is_on(self) -> bool | None:
        """Get huamn exist value."""
        return self.uiid_instance.get_human_exsit_value(self.ewelink_device.device)
