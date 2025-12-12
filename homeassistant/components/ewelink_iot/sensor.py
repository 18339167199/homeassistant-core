"""Sensor platform for eWeLink loT integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import PLATFORM, SENSOR_TYPE, get_uiid_instance


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up eWeLink sensor from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkSensor] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and uiid_instance.platform_config is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            sensor_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.SENSOR
            ]
            for sensor_config in sensor_config_list:
                ewelink_sensor_entity: EWeLinkSensor | None = None
                sensor_type = sensor_config.get("type")
                if sensor_type == SENSOR_TYPE.RSSI:
                    ewelink_sensor_entity = EWeLinkRssiSensor(coordinator, device_id)
                elif sensor_type == SENSOR_TYPE.TEMPERATURE:
                    ewelink_sensor_entity = EWeLinkTemperatureSensor(
                        coordinator, device_id
                    )
                elif sensor_type == SENSOR_TYPE.HUMIDITY:
                    ewelink_sensor_entity = EWeLinkHumiditySensor(
                        coordinator, device_id
                    )
                elif sensor_type == SENSOR_TYPE.BATTERY:
                    ewelink_sensor_entity = EWeLinkBatterySensor(coordinator, device_id)
                if ewelink_sensor_entity:
                    entities.append(ewelink_sensor_entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkSensor(EWeLinkEntity, SensorEntity):
    """Representation of an eWeLink sensor."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id)


class EWeLinkRssiSensor(EWeLinkSensor):
    """EWeLink rssi sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"ewelink_lot_{device_id}_rssi_sensor"

    @property
    def native_value(self):
        """Rssi value."""
        return self.uiid_instance.get_rssi_value(self.ewelink_device.device)


class EWeLinkTemperatureSensor(EWeLinkSensor):
    """EWeLink temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"ewelink_lot_{device_id}_temperature_sensor"

    @property
    def native_unit_of_measurement(self) -> str:
        """Temperature unit."""
        return UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        """Temperature value."""
        return self.uiid_instance.get_temperature_value(self.ewelink_device.device)


class EWeLinkHumiditySensor(EWeLinkSensor):
    """EWeLink humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"ewelink_lot_{device_id}_humidity_sensor"

    @property
    def native_value(self):
        """Humidity value."""
        return self.uiid_instance.get_humidity_value(self.ewelink_device.device)


class EWeLinkBatterySensor(EWeLinkSensor):
    """EWeLink Battery sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: EWeLinkDataCoordinator, device_id: str) -> None:
        """Init."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"ewelink_lot_{device_id}_battery_sensor"

    @property
    def native_value(self) -> int | None:
        """Battery value."""
        return self.uiid_instance.get_battery_value(self.ewelink_device.device)
