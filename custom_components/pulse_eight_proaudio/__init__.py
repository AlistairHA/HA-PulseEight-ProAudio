"""Pulse-Eight ProAudio DSP audio matrix integration."""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.storage import Store
from homeassistant.helpers.typing import ConfigType

from . import websocket_api
from .client import DEFAULT_PORT, ProAudioClient, ProAudioError
from .const import (
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_URL,
)
from .entity import unit_device
from .hub import ProAudioHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

type ProAudioConfigEntry = ConfigEntry[ProAudioHub]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FRONTEND_DIR = Path(__file__).parent / "frontend"
VERSION = "1.1.1"

ENTRY = vol.Optional("config_entry_id")
ZONES = vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=1, max=128))])


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register panel assets, websocket API and services (once)."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
    )
    websocket_api.async_register(hass)
    _register_services(hass)
    return True


async def _ensure_panel(hass: HomeAssistant) -> None:
    if PANEL_URL in hass.data.get(frontend.DATA_PANELS, {}):
        return
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/proaudio-panel.js?v={VERSION}",
        require_admin=False,
        config={},
    )


async def async_setup_entry(hass: HomeAssistant, entry: ProAudioConfigEntry) -> bool:
    client = ProAudioClient(
        entry.data[CONF_HOST],
        entry.data.get(CONF_PORT, DEFAULT_PORT),
        poll_interval=entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
    )
    try:
        await client.start(wait=15)
    except ProAudioError as err:
        raise ConfigEntryNotReady(str(err)) from err

    hub = ProAudioHub(hass, entry.entry_id, entry.title, client)
    await hub.async_load()
    entry.runtime_data = hub

    # Register the unit device first so zone devices can link to it (via_device)
    # regardless of the order the platforms are set up in.
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, **unit_device(hub))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    await _ensure_panel(hass)
    return True


async def _reload(hass: HomeAssistant, entry: ProAudioConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ProAudioConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hub = entry.runtime_data
        hub.close()
        await hub.client.stop()
        others = [e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e.entry_id != entry.entry_id]
        if not others:
            frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: ProAudioConfigEntry) -> None:
    """Delete stored names/presets when the unit is removed."""
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()


# --------------------------------------------------------------------------
# Services
# --------------------------------------------------------------------------

def _hub_for_call(hass: HomeAssistant, call: ServiceCall) -> ProAudioHub:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    wanted = call.data.get("config_entry_id")
    if wanted:
        entries = [e for e in entries if e.entry_id == wanted]
    if not entries:
        raise ServiceValidationError("No matching ProAudio unit is loaded")
    if len(entries) > 1 and not wanted:
        raise ServiceValidationError("Several ProAudio units are set up; specify config_entry_id")
    return entries[0].runtime_data


def _zones(hub: ProAudioHub, call: ServiceCall) -> list[int]:
    zones = list(call.data.get("zones") or [])
    if group := call.data.get("group"):
        zones += hub.group_zones(group)
    if not zones:
        raise ServiceValidationError("Give zones and/or a group")
    return sorted(set(zones))


@callback
def _register_services(hass: HomeAssistant) -> None:
    async def route(call: ServiceCall) -> None:
        hub = _hub_for_call(hass, call)
        source = call.data["source"]
        source = int(source) if str(source).isdigit() else hub.source_by_name(str(source))
        await hub.route(_zones(hub, call), source)

    async def apply_preset(call: ServiceCall) -> None:
        await _hub_for_call(hass, call).async_apply_preset(call.data["preset"])

    async def clear_all(call: ServiceCall) -> None:
        await _hub_for_call(hass, call).clear_all()

    async def zone_power(call: ServiceCall) -> None:
        hub = _hub_for_call(hass, call)
        await hub.zone_power(_zones(hub, call), call.data["on"])

    async def zone_mute(call: ServiceCall) -> None:
        hub = _hub_for_call(hass, call)
        await hub.zone_mute(_zones(hub, call), call.data["mute"])

    async def zone_volume(call: ServiceCall) -> None:
        hub = _hub_for_call(hass, call)
        await hub.zone_volume(_zones(hub, call), call.data["volume"])

    async def send_command(call: ServiceCall) -> dict:
        hub = _hub_for_call(hass, call)
        command = call.data["command"].strip().lstrip("^").rstrip("$")
        if command.upper().startswith(("FS", "IPSET", "IPA", "IPM", "IPG")) and not command.endswith("?"):
            raise ServiceValidationError("Factory-reset and IP changes are blocked from Home Assistant")
        code = await hub.client.raw(command)
        return {"error_code": code}

    hass.services.async_register(
        DOMAIN, "route",
        route, vol.Schema({ENTRY: str, vol.Optional("zones"): ZONES, vol.Optional("group"): str, vol.Required("source"): vol.Any(int, str)}),
    )
    hass.services.async_register(
        DOMAIN, "apply_preset", apply_preset, vol.Schema({ENTRY: str, vol.Required("preset"): str})
    )
    hass.services.async_register(DOMAIN, "clear_all", clear_all, vol.Schema({ENTRY: str}))
    hass.services.async_register(
        DOMAIN, "zone_power", zone_power, vol.Schema({ENTRY: str, vol.Optional("zones"): ZONES, vol.Optional("group"): str, vol.Required("on"): cv.boolean})
    )
    hass.services.async_register(
        DOMAIN, "zone_mute", zone_mute, vol.Schema({ENTRY: str, vol.Optional("zones"): ZONES, vol.Optional("group"): str, vol.Required("mute"): cv.boolean})
    )
    hass.services.async_register(
        DOMAIN, "zone_volume", zone_volume,
        vol.Schema({ENTRY: str, vol.Optional("zones"): ZONES, vol.Optional("group"): str, vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}),
    )
    hass.services.async_register(
        DOMAIN, "send_command", send_command,
        vol.Schema({ENTRY: str, vol.Required("command"): cv.string}),
        supports_response=SupportsResponse.OPTIONAL,
    )
