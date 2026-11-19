"""Buttons: clear all routing, refresh, and one button per routing preset."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ProAudioConfigEntry
from .const import DOMAIN, SIGNAL_PRESETS_UPDATED
from .entity import ProAudioEntity
from .hub import ProAudioHub

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ProAudioConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    hub = entry.runtime_data
    known: dict[str, PresetButton] = {}

    @callback
    def sync_presets() -> None:
        ids = {p["id"] for p in hub.presets}
        new = [PresetButton(hub, pid) for pid in ids - known.keys()]
        for button in new:
            known[button.preset_id] = button
        if new:
            async_add_entities(new)
        registry = er.async_get(hass)
        for pid in list(known.keys() - ids):
            button = known.pop(pid)
            if entity_id := registry.async_get_entity_id("button", DOMAIN, button.unique_id):
                registry.async_remove(entity_id)
        for button in known.values():
            if button.hass:
                button.async_write_ha_state()

    async_add_entities([ClearAllButton(hub), RefreshButton(hub)])
    sync_presets()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_PRESETS_UPDATED.format(entry.entry_id), sync_presets)
    )


class ClearAllButton(ProAudioEntity, ButtonEntity):
    _attr_translation_key = "clear_all"

    def __init__(self, hub: ProAudioHub) -> None:
        super().__init__(hub, "clear_all")

    async def async_press(self) -> None:
        await self.hub.clear_all()


class RefreshButton(ProAudioEntity, ButtonEntity):
    _attr_translation_key = "refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub: ProAudioHub) -> None:
        super().__init__(hub, "refresh")

    async def async_press(self) -> None:
        await self.hub.refresh()


class PresetButton(ProAudioEntity, ButtonEntity):
    """Applies a routing preset defined in the ProAudio panel."""

    def __init__(self, hub: ProAudioHub, preset_id: str) -> None:
        super().__init__(hub, f"preset_{preset_id}")
        self.preset_id = preset_id

    @property
    def _preset(self) -> dict | None:
        return next((p for p in self.hub.presets if p["id"] == self.preset_id), None)

    @property
    def name(self) -> str:
        p = self._preset
        return f"Preset {p['name']}" if p else "Preset"

    @property
    def icon(self) -> str | None:
        p = self._preset
        return p.get("icon") if p else None

    @property
    def extra_state_attributes(self) -> dict:
        p = self._preset or {}
        return {"preset_id": self.preset_id, "zones": sorted(int(z) for z in p.get("routes", {}))}

    async def async_press(self) -> None:
        await self.hub.async_apply_preset(self.preset_id)

