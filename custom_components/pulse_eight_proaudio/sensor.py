"""Status sensors for Pulse-Eight ProAudio."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ProAudioConfigEntry
from .entity import ProAudioEntity
from .hub import ProAudioHub

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    value_fn: Callable[[ProAudioHub], Any]


def _zones(hub: ProAudioHub, pred) -> int:
    return sum(1 for z in range(1, hub.num_zones + 1) if (zs := hub.client.state.zones.get(z)) and pred(zs))


SENSORS = (
    Desc(key="model", translation_key="model", entity_category=EntityCategory.DIAGNOSTIC,
         value_fn=lambda h: h.client.state.model),
    Desc(key="firmware", translation_key="firmware", entity_category=EntityCategory.DIAGNOSTIC,
         value_fn=lambda h: h.client.state.firmware),
    Desc(key="serial", translation_key="serial", entity_category=EntityCategory.DIAGNOSTIC,
         value_fn=lambda h: h.client.state.serial),
    Desc(key="ip_address", translation_key="ip_address", entity_category=EntityCategory.DIAGNOSTIC,
         value_fn=lambda h: h.client.state.ip.get("IPAX") or h.client.host),
    Desc(key="zones_on", translation_key="zones_on", state_class=SensorStateClass.MEASUREMENT,
         value_fn=lambda h: _zones(h, lambda z: z.power)),
    Desc(key="zones_routed", translation_key="zones_routed", state_class=SensorStateClass.MEASUREMENT,
         value_fn=lambda h: _zones(h, lambda z: z.source)),
    Desc(key="last_error", translation_key="last_error", entity_category=EntityCategory.DIAGNOSTIC,
         value_fn=lambda h: (f"{e['code']}: {e['message']}" if (e := (list(h.client.state.errors) or [None])[-1]) else "none")),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ProAudioConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    hub = entry.runtime_data
    async_add_entities(ProAudioSensor(hub, d) for d in SENSORS)


class ProAudioSensor(ProAudioEntity, SensorEntity):
    entity_description: Desc

    def __init__(self, hub: ProAudioHub, description: Desc) -> None:
        super().__init__(hub, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value_fn(self.hub)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "ip_address":
            s = self.hub.client.state
            return {"mask": s.ip.get("IPMX"), "gateway": s.ip.get("IPGX"), "mode": s.ip.get("mode"),
                    "port": self.hub.client.port}
        if self.entity_description.key == "last_error":
            e = list(self.hub.client.state.errors)
            return {"command": e[-1]["command"]} if e else None
        return None
