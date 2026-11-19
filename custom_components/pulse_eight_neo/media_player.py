"""One media_player per matrix output: source = routed input, power = CEC to the display."""

from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .client import CEC_KEYS
from .const import DOMAIN
from .entity import NeoOutputEntity, unit_id

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    add(NeoOutput(hub, b) for b in sorted(hub.outputs))


class NeoOutput(NeoOutputEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_device_class = MediaPlayerDeviceClass.TV
    _attr_supported_features = (
        MediaPlayerEntityFeature.SELECT_SOURCE | MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.VOLUME_STEP | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.PLAY | MediaPlayerEntityFeature.PAUSE | MediaPlayerEntityFeature.STOP
    )

    def __init__(self, hub, bay: int) -> None:
        super().__init__(hub, bay, "player")
        self._known_name = hub.output_name(bay)

    @callback
    def _update(self) -> None:
        # names live on the matrix: keep the HA device name in step (unless renamed in HA)
        name = self.hub.output_name(self.bay)
        if name != self._known_name:
            self._known_name = name
            reg = dr.async_get(self.hass)
            dev = reg.async_get_device(identifiers={(DOMAIN, f"{unit_id(self.hub)}_out{self.bay}")})
            if dev and not dev.name_by_user:
                reg.async_update_device(dev.id, name=name)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.hub.add_listener(self._update))

    @property
    def state(self) -> MediaPlayerState | None:
        p = self.hub.tv_power(self.bay)
        if p in ("on", "turning_on"):
            return MediaPlayerState.ON
        if p in ("standby", "turning_off"):
            return MediaPlayerState.OFF
        return MediaPlayerState.ON  # CEC power unknown: the output itself is live

    @property
    def source_list(self) -> list[str]:
        hidden = set(self.hub.settings["hidden_inputs"])
        return [self.hub.input_name(b) for b in self.hub.video_input_bays()
                if b + 1 not in hidden and self.hub.source_allowed(self.bay, b)]

    @property
    def source(self) -> str | None:
        s = self.hub.source_of(self.bay)
        return self.hub.input_name(s) if s is not None else None

    @property
    def extra_state_attributes(self) -> dict:
        a = self.hub.audio_source_of(self.bay)
        return {"output": self.bay + 1, "tv_power": self.hub.tv_power(self.bay),
                "audio_source": self.hub.input_name(a) if a is not None else None, "hdbaset": self.hub.is_hdbt(self.bay),
                "port_type": self.hub.port_type(self.bay) or None}

    async def async_select_source(self, source: str) -> None:
        await self.hub.route([self.bay], self.hub.input_by_name(source))

    async def async_turn_on(self) -> None:
        await self.hub.cec_power("Output", [self.bay], True)

    async def async_turn_off(self) -> None:
        await self.hub.cec_power("Output", [self.bay], False)

    async def _key(self, name: str) -> None:
        await self.hub.cec_key("Output", self.bay, CEC_KEYS[name])

    async def async_volume_up(self) -> None:
        await self.hub.cec_volume("Up", "Output", self.bay)

    async def async_volume_down(self) -> None:
        await self.hub.cec_volume("Down", "Output", self.bay)

    async def async_mute_volume(self, mute: bool) -> None:
        # CEC mute is a toggle on the matrix; HA's requested state can't be enforced
        await self.hub.cec_volume("Mute", "Output", self.bay)

    async def async_media_play(self) -> None:
        await self._key("play")

    async def async_media_pause(self) -> None:
        await self._key("pause")

    async def async_media_stop(self) -> None:
        await self._key("stop")
