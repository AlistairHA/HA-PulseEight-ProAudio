"""Diagnostics: raw API payloads (serial/MAC redacted) to map unknown firmware fields."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data

from . import NeoConfigEntry

REDACT = {"Serial", "serial", "MAC", "Mac", "mac", "password", "InstallerId"}


async def async_get_config_entry_diagnostics(hass, entry: NeoConfigEntry) -> dict:
    h = entry.runtime_data
    return async_redact_data({
        "details": h.details, "features": h.features, "health": h.health, "modes": h.modes,
        "inputs": h.inputs, "outputs": h.outputs, "output_details": h.out_details, "input_details": h.in_details,
        "remote_details": h.remote,
    }, REDACT)
