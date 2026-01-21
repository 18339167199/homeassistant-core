"""Switch platform for eWeLink IoT integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import COORDINATOR, DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .entity import EWeLinkEntity
from .uiid import PLATFORM, SELECT_TYPE, get_uiid_instance


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up eWeLink switches from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    entities: list[EWeLinkSelectEntity] = []

    for device_id, device in coordinator.data.items():
        uiid_instance = get_uiid_instance(device.uiid)
        if (
            uiid_instance is not None
            and uiid_instance.platform_config is not None
            and isinstance(uiid_instance.platform_config, list)
            and len(uiid_instance.platform_config) > 0
        ):
            select_config_list = [
                config
                for config in uiid_instance.platform_config
                if config["platform"] == PLATFORM.SELECT
            ]
            for select_config in select_config_list:
                entity: EWeLinkSelectEntity | None = None
                select_type = select_config.get("type")
                if select_type == SELECT_TYPE.STARTUP:
                    entity = EWeLinkStartupEntity(
                        coordinator, device_id, select_config.get("config", {})
                    )
                if entity is not None:
                    entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class EWeLinkSelectEntity(EWeLinkEntity, SelectEntity):
    """Representation of an select options."""

    def __init__(
        self, coordinator: EWeLinkDataCoordinator, device_id: str, config=None
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, device_id)
        self.config = config
        self._attr_unique_id = f"ewelink_lot_{device_id}_select"
        self._attr_name = None  # Use device name


class EWeLinkStartupEntity(EWeLinkSelectEntity):
    """Startup select entity."""

    @property
    def outlet(self):
        """Outlet."""
        if self.config:
            return self.config.get("outlet")
        return None

    @property
    def current_option(self) -> str | None:
        """Return current state."""
        if not self.ewelink_device or not self.uiid_instance:
            return None
        return self.uiid_instance.get_startup_value(
            self.ewelink_device.device, self.outlet
        )

    @property
    def options(self) -> list[str]:
        """Startup options."""
        if self.config and "options" in self.config:
            return self.config.get("options")
        return []

    async def async_select_option(self, option: str) -> None:
        """Select startup."""
        if not self.ewelink_device:
            return
        params = self.uiid_instance.gen_control_startup_params(option, self.outlet)
        result = await self.coordinator.control_device(self.ewelink_device, params)
        if result and result.get("error") == 0:
            self._async_write_ha_state()
