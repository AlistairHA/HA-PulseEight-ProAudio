"""Buttons: restart, refresh details, one per routing preset."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .const import DOMAIN, SIGNAL_SETTINGS
from .entity import NeoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    known: dict[str, PresetButton] = {}

    @callback
    def sync() -> None:
        ids = {p["id"] for p in hub.presets}
        new = [PresetButton(hub, i) for i in ids - known.keys()]
        for b in new:
            known[b.preset_id] = b
        if new:
            add(new)
        reg = er.async_get(hass)
        for pid in list(known.keys() - ids):
            b = known.pop(pid)
            if eid := reg.async_get_entity_id("button", DOMAIN, b.unique_id):
                reg.async_remove(eid)

    add([Restart(hub), Refresh(hub)])
    sync()
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_SETTINGS.format(entry.entry_id), sync))


class Restart(NeoEntity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hub) -> None:
        super().__init__(hub, "restart")

    async def async_press(self) -> None:
        await self.hub.restart()


class Refresh(NeoEntity, ButtonEntity):
    _attr_translation_key = "refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub) -> None:
        super().__init__(hub, "refresh")

    async def async_press(self) -> None:
        await self.hub.refresh_details()


class PresetButton(NeoEntity, ButtonEntity):
    def __init__(self, hub, pid: str) -> None:
        super().__init__(hub, f"preset_{pid}")
        self.preset_id = pid

    @property
    def _p(self):
        return next((p for p in self.hub.presets if p["id"] == self.preset_id), None)

    @property
    def name(self) -> str:
        return f"Preset {self._p['name']}" if self._p else "Preset"

    @property
    def icon(self):
        return self._p.get("icon") if self._p else None

    async def async_press(self) -> None:
        await self.hub.apply_preset(self.preset_id)
