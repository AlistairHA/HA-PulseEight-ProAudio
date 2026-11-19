"""Binary sensors: connectivity, input signal, output display/link."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .client import as_bool, first
from .entity import NeoEntity, NeoOutputEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    ents: list[BinarySensorEntity] = [Connected(hub)]
    ents += [InputSignal(hub, b) for b in sorted(hub.inputs)]
    for b in sorted(hub.outputs):
        ents.append(DisplayConnected(hub, b))
        if hub.is_hdbt(b):
            ents.append(Linked(hub, b))
    add(ents)


class Connected(NeoEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub) -> None:
        super().__init__(hub, "connected")

    @property
    def available(self) -> bool:
        return True

    @property
    def is_on(self) -> bool:
        return self.hub.connected


class InputSignal(NeoEntity, BinarySensorEntity):
    _attr_translation_key = "input_signal"

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, f"in{bay}_signal")
        self.bay = bay

    @property
    def name(self) -> str:
        return f"Input {self.bay + 1} {self.hub.input_name(self.bay)} signal"

    @property
    def is_on(self):
        return as_bool(first(self.hub.inputs.get(self.bay), "HasSignal"))


class DisplayConnected(NeoOutputEntity, BinarySensorEntity):
    _attr_translation_key = "display_connected"
    _attr_device_class = BinarySensorDeviceClass.PLUG

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "hpd")

    @property
    def is_on(self):
        return as_bool(first(self.hub.outputs.get(self.bay), "HPD"))


class Linked(NeoOutputEntity, BinarySensorEntity):
    _attr_translation_key = "hdbaset_link"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "linked")

    @property
    def is_on(self):
        return as_bool(first(self.hub.out_details.get(self.bay), "LinkStatus"))
