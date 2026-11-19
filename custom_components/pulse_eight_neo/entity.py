"""Base entities for Pulse-Eight neo."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.entity import Entity

from .client import first
from .const import DOMAIN, MANUFACTURER
from .hub import NeoHub


def unit_id(hub: NeoHub) -> str:
    return hub.serial or hub.entry_id


def unit_device(hub: NeoHub) -> DeviceInfo:
    info = DeviceInfo(
        identifiers={(DOMAIN, unit_id(hub))}, manufacturer=MANUFACTURER, model=hub.model_name,
        model_id=hub.model_code or None, name=hub.title, serial_number=hub.serial,
        sw_version=first(hub.details, "Version"), hw_version=(str(v) if (v := first(hub.details, "HardwareRevision", "BoardRev")) is not None else None),
        configuration_url=hub.client.base_url,
    )
    if mac := first(hub.details, "MAC", "Mac"):
        info["connections"] = {(CONNECTION_NETWORK_MAC, format_mac(str(mac)))}
    return info


def output_device(hub: NeoHub, bay: int) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{unit_id(hub)}_out{bay}")}, manufacturer=MANUFACTURER,
        model="HDBaseT output" if hub.is_hdbt(bay) else "HDMI output",
        name=hub.output_name(bay), via_device=(DOMAIN, unit_id(hub)),
    )


class NeoEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hub: NeoHub, key: str) -> None:
        self.hub = hub
        self._attr_unique_id = f"{unit_id(hub)}_{key}"
        self._attr_device_info = unit_device(hub)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.add_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return self.hub.connected


class NeoOutputEntity(NeoEntity):
    def __init__(self, hub: NeoHub, bay: int, key: str) -> None:
        super().__init__(hub, f"out{bay}_{key}")
        self.bay = bay
        self._attr_device_info = output_device(hub, bay)
