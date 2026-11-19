"""Unit power for Pulse-Eight ProAudio."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ProAudioConfigEntry
from .entity import ProAudioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ProAudioConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([UnitPower(entry.runtime_data)])


class UnitPower(ProAudioEntity, SwitchEntity):
    _attr_translation_key = "power"

    def __init__(self, hub) -> None:
        super().__init__(hub, "power")

    @property
    def is_on(self) -> bool | None:
        p = self.hub.client.state.power
        return None if p is None else p in (1, 3)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"locked_on": self.hub.client.state.power == 3}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hub.unit_power(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hub.unit_power(False)
