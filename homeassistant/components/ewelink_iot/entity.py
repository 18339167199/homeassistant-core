"""Base entity for eWeLink IoT integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EWeLinkDataCoordinator


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
        self._device_id = device_id

        device = coordinator.data[device_id]

        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device.name,
            manufacturer=device.brand_name or "eWeLink",
            model=device.product_model,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        device = self.coordinator.data.get(self._device_id)
        return device is not None and device.online
