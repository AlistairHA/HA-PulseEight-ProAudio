"""Pulse-Eight neo video matrix (neo:X, neo:X+ and family)."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from . import websocket_api
from .client import CEC_KEYS, NeoAuthError, NeoClient, NeoError
from .const import (
    CONF_DETAIL_INTERVAL,
    CONF_UDP,
    CONF_UDP_PORT,
    DEFAULT_UDP,
    DEFAULT_UDP_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_DETAIL_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PANEL_ELEMENT,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    STATIC_URL,
)
from .entity import unit_device
from .hub import NeoHub

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.MEDIA_PLAYER, Platform.REMOTE, Platform.SELECT, Platform.SENSOR, Platform.SWITCH]
VERSION = "1.0.0"
type NeoConfigEntry = ConfigEntry[NeoHub]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), cache_headers=False)]
    )
    websocket_api.async_register(hass)
    _register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry) -> bool:
    client = NeoClient(entry.data[CONF_HOST], entry.data.get(CONF_PASSWORD, ""))
    hub = NeoHub(hass, entry.entry_id, entry.title, client,
                 fast=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                 slow=entry.options.get(CONF_DETAIL_INTERVAL, DEFAULT_DETAIL_INTERVAL))
    try:
        await hub.first_refresh()
    except NeoAuthError as err:
        await client.close()
        raise ConfigEntryAuthFailed(str(err)) from err
    except NeoError as err:
        await client.close()
        raise ConfigEntryNotReady(str(err)) from err
    await hub.async_load()
    entry.runtime_data = hub
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, **unit_device(hub))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    hub.start()
    if entry.options.get(CONF_UDP, DEFAULT_UDP):
        await hub.start_udp(entry.options.get(CONF_UDP_PORT, DEFAULT_UDP_PORT))
    entry.async_on_unload(entry.add_update_listener(_reload))
    if PANEL_URL not in hass.data.get(frontend.DATA_PANELS, {}):
        await panel_custom.async_register_panel(
            hass, frontend_url_path=PANEL_URL, webcomponent_name=PANEL_ELEMENT, sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON, module_url=f"{STATIC_URL}/neo-panel.js?v={VERSION}", require_admin=False, config={},
        )
    return True


async def _reload(hass: HomeAssistant, entry: NeoConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: NeoConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.stop()
        if not [e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e.entry_id != entry.entry_id]:
            frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
    return ok


async def async_remove_entry(hass: HomeAssistant, entry: NeoConfigEntry) -> None:
    from homeassistant.helpers.storage import Store

    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()


# ---------------------------------------------------------------------------
ENTRY = vol.Optional("config_entry_id")
PORTS = vol.All(cv.ensure_list, [vol.Any(int, str)])


def _hub(hass: HomeAssistant, call: ServiceCall) -> NeoHub:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if wanted := call.data.get("config_entry_id"):
        entries = [e for e in entries if e.entry_id == wanted]
    if not entries:
        raise ServiceValidationError("No matching neo matrix is loaded")
    if len(entries) > 1 and not call.data.get("config_entry_id"):
        raise ServiceValidationError("Several neo matrices are set up; give config_entry_id")
    return entries[0].runtime_data


def _outputs(hub: NeoHub, call: ServiceCall) -> list[int]:
    outs = [hub.output_by_name(o) for o in call.data.get("outputs") or []]
    if g := call.data.get("group"):
        outs += hub.group_outputs(g)
    if not outs:
        raise ServiceValidationError("Give outputs and/or a group")
    return sorted(set(outs))


@callback
def _register_services(hass: HomeAssistant) -> None:
    async def route(call: ServiceCall) -> None:
        hub = _hub(hass, call)
        await hub.route(_outputs(hub, call), hub.input_by_name(call.data["input"]), power_on=call.data.get("power_on", False))

    async def route_audio(call: ServiceCall) -> None:
        hub = _hub(hass, call)
        src = call.data["input"]
        await hub.audio_route(_outputs(hub, call), -1 if str(src) in ("0", "none") else hub.input_by_name(src))

    async def cec_power(call: ServiceCall) -> None:
        hub = _hub(hass, call)
        await hub.cec_power("Output", _outputs(hub, call), call.data["on"])

    async def cec_key(call: ServiceCall) -> None:
        hub = _hub(hass, call)
        key = str(call.data["key"]).lower()
        code = CEC_KEYS.get(key)
        if code is None:
            try:
                code = int(key, 0)
            except ValueError as err:
                raise ServiceValidationError(f"Unknown CEC key '{key}'") from err
        for o in _outputs(hub, call):
            await hub.cec_key("Output", o, code)

    async def cec_volume(call: ServiceCall) -> None:
        hub = _hub(hass, call)
        method = {"up": "Up", "down": "Down", "mute": "Mute"}[call.data["action"]]
        for o in _outputs(hub, call):
            await hub.cec_volume(method, "Output", o)

    async def apply_preset(call: ServiceCall) -> None:
        await _hub(hass, call).apply_preset(call.data["preset"])

    async def refresh(call: ServiceCall) -> None:
        await _hub(hass, call).refresh_details()

    async def get_status(call: ServiceCall) -> dict:
        snap = _hub(hass, call).snapshot()
        return {"outputs": [{k: o[k] for k in ("zone", "name", "source", "tv_power", "signal")} | {"input": next((i["name"] for i in snap["inputs"] if i["source"] == o["source"]), None)} for o in snap["outputs"]]}

    base = {ENTRY: str, vol.Optional("outputs"): PORTS, vol.Optional("group"): str}
    hass.services.async_register(DOMAIN, "route", route, vol.Schema({**base, vol.Required("input"): vol.Any(int, str), vol.Optional("power_on", default=False): cv.boolean}))
    hass.services.async_register(DOMAIN, "route_audio", route_audio, vol.Schema({**base, vol.Required("input"): vol.Any(int, str)}))
    hass.services.async_register(DOMAIN, "cec_power", cec_power, vol.Schema({**base, vol.Required("on"): cv.boolean}))
    hass.services.async_register(DOMAIN, "cec_key", cec_key, vol.Schema({**base, vol.Required("key"): cv.string}))
    hass.services.async_register(DOMAIN, "cec_volume", cec_volume, vol.Schema({**base, vol.Required("action"): vol.In(["up", "down", "mute"])}))
    hass.services.async_register(DOMAIN, "apply_preset", apply_preset, vol.Schema({ENTRY: str, vol.Required("preset"): str}))
    hass.services.async_register(DOMAIN, "refresh", refresh, vol.Schema({ENTRY: str}))
    hass.services.async_register(DOMAIN, "get_status", get_status, vol.Schema({ENTRY: str}), supports_response=SupportsResponse.ONLY)
