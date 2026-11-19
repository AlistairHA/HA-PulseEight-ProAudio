"""Switches: front-panel status LEDs and matrix-wide CEC behaviour."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .client import first
from .entity import NeoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    ents: list[SwitchEntity] = []
    if first(hub.features, "StatusLED") is not None:
        ents.append(StatusLed(hub))
    ents += [CecOption(hub, k) for k in ("cec", "cec_switching", "autopause", "combokeys") if hub.cec_option(k) is not None]
    add(ents)


class StatusLed(NeoEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "status_led"

    def __init__(self, hub) -> None:
        super().__init__(hub, "status_led")

    @property
    def is_on(self) -> bool | None:
        v = first(self.hub.features, "StatusLED")
        return None if v is None else str(v).lower() not in ("off", "0", "false")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hub.set_status_led(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hub.set_status_led(False)


class CecOption(NeoEntity, SwitchEntity):
    """CEC enabled / automatic switching / auto-pause / combination keys."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hub, key: str) -> None:
        super().__init__(hub, f"cec_opt_{key}")
        self.key = key
        self._attr_translation_key = f"cec_{key}" if not key.startswith("cec") else key

    @property
    def is_on(self) -> bool | None:
        return self.hub.cec_option(self.key)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hub.set_cec_option(self.key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hub.set_cec_option(self.key, False)
