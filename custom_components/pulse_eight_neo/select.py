"""Selects: input EDID profile, front-panel backlight, IR profile per output."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .client import BACKLIGHT_OPTIONS, first
from .entity import NeoEntity, NeoOutputEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    ents: list[SelectEntity] = [InputEdid(hub, b) for b in hub.video_input_bays() if hub.edid_profile(b) is not None]
    if first(hub.features, "BacklightLED") is not None:
        ents.append(Backlight(hub))
    if hub.ir_profiles:
        ents += [IrProfile(hub, b) for b in sorted(hub.outputs)]
    add(ents)


class InputEdid(NeoEntity, SelectEntity):
    """EDID the matrix presents to a source (what resolution/audio it should send)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "input_edid"

    def __init__(self, hub, bay: int) -> None:
        super().__init__(hub, f"in{bay}_edid")
        self.bay = bay
        self._attr_translation_placeholders = {"input": str(bay + 1)}

    def _opts(self) -> dict[str, int]:
        opts = {label: v for v, label in self.hub.edid_options().items()}
        cur = self.hub.edid_profile(self.bay)
        if cur is not None and cur not in opts.values():
            opts[f"Custom profile {cur}"] = cur
        return opts

    @property
    def options(self) -> list[str]:
        return list(self._opts())

    @property
    def current_option(self) -> str | None:
        cur = self.hub.edid_profile(self.bay)
        return next((k for k, v in self._opts().items() if v == cur), None)

    @property
    def extra_state_attributes(self) -> dict:
        return {"input": self.hub.input_name(self.bay), "profile_id": self.hub.edid_profile(self.bay)}

    async def async_select_option(self, option: str) -> None:
        await self.hub.set_edid(self.bay, self._opts()[option])


class Backlight(NeoEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "backlight"
    _attr_options = list(BACKLIGHT_OPTIONS)

    def __init__(self, hub) -> None:
        super().__init__(hub, "backlight")

    @property
    def current_option(self) -> str | None:
        v = str(first(self.hub.features, "BacklightLED", default="")).lower()
        # some firmware reports a level ("high") rather than on/off/auto
        return v if v in BACKLIGHT_OPTIONS else "on" if v in ("high", "low", "medium") else None

    async def async_select_option(self, option: str) -> None:
        await self.hub.set_backlight(option)


class IrProfile(NeoOutputEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "ir_profile"
    _attr_entity_registry_enabled_default = False

    def __init__(self, hub, bay: int) -> None:
        super().__init__(hub, bay, "ir_profile")

    def _opts(self) -> dict[str, int]:
        return {f"{first(p, 'Id')}: {first(p, 'Name', default='Profile')}": int(first(p, "Id")) for p in self.hub.ir_profiles}

    @property
    def options(self) -> list[str]:
        return list(self._opts())

    @property
    def current_option(self) -> str | None:
        cur = self.hub.ir_profile(self.bay)
        return next((k for k, v in self._opts().items() if v == cur), None)

    async def async_select_option(self, option: str) -> None:
        await self.hub.set_ir_profile(self.bay, self._opts()[option])
