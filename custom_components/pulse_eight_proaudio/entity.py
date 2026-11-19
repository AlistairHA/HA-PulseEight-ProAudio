"""Base entities for Pulse-Eight ProAudio."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER
from .hub import ProAudioHub


def unit_id(hub: ProAudioHub) -> str:
    return hub.client.state.serial or hub.entry_id


def unit_device(hub: ProAudioHub) -> DeviceInfo:
    s = hub.client.state
    return DeviceInfo(
        identifiers={(DOMAIN, unit_id(hub))},
        manufacturer=MANUFACTURER,
        model=s.model or "ProAudio",
        name=f"{hub.title}",
        serial_number=s.serial,
        sw_version=s.firmware,
    )


def zone_device(hub: ProAudioHub, zone: int) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, f"{unit_id(hub)}_zone{zone}")},
        manufacturer=MANUFACTURER,
        model=f"{hub.client.state.model or 'ProAudio'} zone",
        name=hub.zone_name(zone),
        via_device=(DOMAIN, unit_id(hub)),
    )


class ProAudioEntity(Entity):
    """Push-updated entity bound to a hub."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hub: ProAudioHub, key: str) -> None:
        self.hub = hub
        self._attr_unique_id = f"{unit_id(hub)}_{key}"
        self._attr_device_info = unit_device(hub)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.client.add_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return self.hub.client.state.connected
