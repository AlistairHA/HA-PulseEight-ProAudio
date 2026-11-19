"""One media_player per ProAudio output zone (source, volume, mute, power)."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ProAudioConfigEntry
from .const import DOMAIN, SIGNAL_PRESETS_UPDATED
from .entity import ProAudioEntity, unit_id, zone_device

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ProAudioConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    hub = entry.runtime_data
    async_add_entities(ProAudioZonePlayer(hub, z) for z in range(1, hub.num_zones + 1))


class ProAudioZonePlayer(ProAudioEntity, MediaPlayerEntity):
    _attr_name = None  # use the zone device's name
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
    )

    def __init__(self, hub, zone: int) -> None:
        super().__init__(hub, f"zone{zone}")
        self.zone = zone
        self._attr_device_info = zone_device(hub, zone)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_PRESETS_UPDATED.format(self.hub.entry_id), self._settings_changed
            )
        )

    @callback
    def _settings_changed(self) -> None:
        """Zone renamed in the panel: rename the device (unless the user renamed it in HA)."""
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(identifiers={(DOMAIN, f"{unit_id(self.hub)}_zone{self.zone}")})
        if device and device.name != self.hub.zone_name(self.zone):
            registry.async_update_device(device.id, name=self.hub.zone_name(self.zone))
        self.async_write_ha_state()

    @property
    def _z(self):
        return self.hub.client.state.zones.get(self.zone)

    @property
    def state(self) -> MediaPlayerState | None:
        z = self._z
        if not self.hub.client.state.is_on or z is None or z.power is False:
            return MediaPlayerState.OFF
        return MediaPlayerState.ON

    @property
    def source_list(self) -> list[str]:
        return [self.hub.input_name(i.source) for i in self.hub.visible_inputs()]

    @property
    def source(self) -> str | None:
        z = self._z
        if z is None or z.source is None:
            return None
        return self.hub.input_name(z.source) if z.source else None

    @property
    def volume_level(self) -> float | None:
        z = self._z
        return None if z is None or z.volume is None else z.volume / 100

    @property
    def is_volume_muted(self) -> bool | None:
        z = self._z
        return None if z is None else z.muted

    @property
    def extra_state_attributes(self) -> dict:
        z = self._z
        return {
            "zone": self.zone,
            "source_number": z.source if z else None,
            "audio_type": z.audio_type if z else None,
        }

    async def async_select_source(self, source: str) -> None:
        await self.hub.route([self.zone], self.hub.source_by_name(source))

    async def async_set_volume_level(self, volume: float) -> None:
        await self.hub.zone_volume([self.zone], round(volume * 100))

    async def async_volume_up(self) -> None:
        await self.hub._run(self.hub.client.step_zone_volume([self.zone], 2))

    async def async_volume_down(self) -> None:
        await self.hub._run(self.hub.client.step_zone_volume([self.zone], -2))

    async def async_mute_volume(self, mute: bool) -> None:
        await self.hub.zone_mute([self.zone], mute)

    async def async_turn_on(self) -> None:
        if not self.hub.client.state.is_on:
            await self.hub.unit_power(True)
        await self.hub.zone_power([self.zone], True)

    async def async_turn_off(self) -> None:
        await self.hub.zone_power([self.zone], False)
