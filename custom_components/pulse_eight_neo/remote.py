"""CEC remotes: one per output (the TV/AVR) and one per video input (the source device)."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import ATTR_DELAY_SECS, ATTR_NUM_REPEATS, RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NeoConfigEntry
from .client import CEC_KEYS
from .entity import NeoEntity, NeoOutputEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    add([OutputRemote(hub, b) for b in sorted(hub.outputs)] + [InputRemote(hub, b) for b in hub.video_input_bays()])


def _codes(command: Iterable[str]) -> list[int]:
    out = []
    for c in command:
        key = str(c).strip().lower()
        if key in CEC_KEYS:
            out.append(CEC_KEYS[key])
            continue
        try:
            out.append(int(key, 0))
        except ValueError as err:
            raise ServiceValidationError(f"Unknown CEC key '{c}'. Use a key name ({', '.join(sorted(CEC_KEYS))}) or a code such as 0x44") from err
    return out


class _CecRemote:
    mode = "Output"

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        codes = _codes(command)  # validate everything before sending anything
        repeats = int(kwargs.get(ATTR_NUM_REPEATS, 1))
        delay = float(kwargs.get(ATTR_DELAY_SECS, 0.4))
        for n in range(repeats):
            for i, code in enumerate(codes):
                if n or i:
                    await asyncio.sleep(delay)
                await self.hub.cec_key(self.mode, self.bay, code)


class OutputRemote(_CecRemote, NeoOutputEntity, RemoteEntity):
    _attr_translation_key = "display_remote"

    def __init__(self, hub, bay: int) -> None:
        super().__init__(hub, bay, "remote")

    @property
    def is_on(self) -> bool | None:
        p = self.hub.tv_power(self.bay)
        return None if p is None else p in ("on", "turning_on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hub.cec_power("Output", [self.bay], True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hub.cec_power("Output", [self.bay], False)


class InputRemote(_CecRemote, NeoEntity, RemoteEntity):
    """Keys sent to the source device on an input (e.g. Sky Q, Apple TV) over CEC."""

    mode = "Input"
    _attr_translation_key = "source_remote"
    _attr_entity_registry_enabled_default = False

    def __init__(self, hub, bay: int) -> None:
        super().__init__(hub, f"in{bay}_remote")
        self.bay = bay
        self._attr_translation_placeholders = {"input": str(bay + 1)}

    @property
    def is_on(self) -> bool:
        return True

    @property
    def extra_state_attributes(self) -> dict:
        return {"input": self.hub.input_name(self.bay)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hub.cec_key("Input", self.bay, CEC_KEYS["power_on"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hub.cec_key("Input", self.bay, CEC_KEYS["power_off"])
