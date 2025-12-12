"""Base entity for eWeLink IoT integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import EWeLinkDevice
from .const import DOMAIN
from .coordinator import EWeLinkDataCoordinator
from .uiid import get_uiid_instance
from .utils import get_device_uiid


class EWeLinkEntity(CoordinatorEntity[EWeLinkDataCoordinator]):
    """Base entity for eWeLink devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EWeLinkDataCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        device: EWeLinkDevice = coordinator.data[device_id]
        uiid = get_device_uiid(device.device)
        self.device_id = device_id
        self.uiid = uiid
        self.uiid_instance: Any = get_uiid_instance(uiid)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.device_name,
            manufacturer=device.brand_name,
            model=device.model,
            serial_number=device_id,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        device = self.coordinator.data.get(self.device_id)
        return device is not None and device.online

    @property
    def ewelink_device(self) -> EWeLinkDevice:
        """Get EWeLinkDevice instance."""
        return self.coordinator.data.get(self.device_id)  # type: ignore  # noqa: PGH003
