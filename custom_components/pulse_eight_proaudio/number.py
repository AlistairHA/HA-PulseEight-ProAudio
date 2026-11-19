"""Master volume for Pulse-Eight ProAudio."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfSoundPressure
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ProAudioConfigEntry
from .client import master_db, master_raw
from .entity import ProAudioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ProAudioConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([MasterVolume(entry.runtime_data)])


class MasterVolume(ProAudioEntity, NumberEntity):
    """Master volume in dB (-100 = full mute, 0 = unity, up to +24)."""

    _attr_translation_key = "master_volume"
    _attr_native_min_value = -100
    _attr_native_max_value = 24
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfSoundPressure.DECIBEL
    _attr_mode = NumberMode.SLIDER

    def __init__(self, hub) -> None:
        super().__init__(hub, "master_volume")

    @property
    def native_value(self) -> float | None:
        return master_db(self.hub.client.state.master_volume)

    async def async_set_native_value(self, value: float) -> None:
        await self.hub.master_volume(master_raw(value))
