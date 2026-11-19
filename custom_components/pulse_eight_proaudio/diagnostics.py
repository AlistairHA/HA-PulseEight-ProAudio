"""Diagnostics for Pulse-Eight ProAudio."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import ProAudioConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ProAudioConfigEntry) -> dict[str, Any]:
    snap = entry.runtime_data.snapshot()
    snap["serial"] = "**REDACTED**" if snap.get("serial") else None
    return snap
