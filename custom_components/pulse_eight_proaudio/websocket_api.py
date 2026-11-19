"""WebSocket API used by the ProAudio sidebar panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .hub import ProAudioHub

ZONES = vol.All([vol.Coerce(int)], vol.Length(min=1))


def _hubs(hass: HomeAssistant) -> dict[str, ProAudioHub]:
    return {
        e.entry_id: e.runtime_data
        for e in hass.config_entries.async_loaded_entries(DOMAIN)
        if getattr(e, "runtime_data", None) is not None
    }


def _hub(hass: HomeAssistant, entry_id: str) -> ProAudioHub:
    hub = _hubs(hass).get(entry_id)
    if hub is None:
        raise HomeAssistantError(f"ProAudio unit {entry_id} not loaded")
    return hub


@callback
def async_register(hass: HomeAssistant) -> None:
    for handler in (
        ws_list_units, ws_subscribe, ws_route, ws_clear_all, ws_zone_power, ws_zone_mute,
        ws_zone_volume, ws_master_volume, ws_unit_power, ws_refresh, ws_set_names,
        ws_save_preset, ws_delete_preset, ws_save_groups, ws_apply_preset, ws_reorder_presets,
    ):
        websocket_api.async_register_command(hass, handler)


def _wrap(func):
    """Run a hub coroutine and translate errors into websocket errors."""

    async def handler(hass, connection, msg):
        try:
            result = await func(_hub(hass, msg["entry_id"]), msg)
        except HomeAssistantError as err:
            connection.send_error(msg["id"], "proaudio_error", str(err))
            return
        connection.send_result(msg["id"], result)

    return handler


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_units"})
@callback
def ws_list_units(hass, connection, msg) -> None:
    connection.send_result(
        msg["id"],
        [{"entry_id": eid, "title": hub.title, "model": hub.client.state.model}
         for eid, hub in _hubs(hass).items()],
    )


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/subscribe", vol.Required("entry_id"): str}
)
@callback
def ws_subscribe(hass, connection, msg) -> None:
    try:
        hub = _hub(hass, msg["entry_id"])
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    pending = {"handle": None}

    @callback
    def send() -> None:
        pending["handle"] = None
        connection.send_message(websocket_api.event_message(msg["id"], hub.snapshot()))

    @callback
    def changed() -> None:
        if pending["handle"] is None:  # coalesce bursts (e.g. a full refresh)
            pending["handle"] = hass.loop.call_later(0.1, send)

    unsub = hub.add_listener(changed)

    @callback
    def cancel() -> None:
        unsub()
        if pending["handle"]:
            pending["handle"].cancel()

    connection.subscriptions[msg["id"]] = cancel
    connection.send_result(msg["id"])
    send()


def _cmd(schema: dict, *, admin: bool = False):
    def decorator(func):
        handler = websocket_api.async_response(_wrap(func))
        if admin:
            handler = websocket_api.require_admin(handler)
        return websocket_api.websocket_command(
            {vol.Required("type"): f"{DOMAIN}/{func.__name__.removeprefix('ws_')}",
             vol.Required("entry_id"): str, **schema}
        )(handler)

    return decorator


@_cmd({vol.Required("zones"): ZONES, vol.Required("source"): vol.All(vol.Coerce(int), vol.Range(min=0, max=160))})
async def ws_route(hub: ProAudioHub, msg: dict[str, Any]):
    await hub.route(msg["zones"], msg["source"])


@_cmd({})
async def ws_clear_all(hub: ProAudioHub, msg):
    await hub.clear_all()


@_cmd({vol.Required("zones"): ZONES, vol.Required("on"): bool})
async def ws_zone_power(hub: ProAudioHub, msg):
    await hub.zone_power(msg["zones"], msg["on"])


@_cmd({vol.Required("zones"): ZONES, vol.Required("mute"): bool})
async def ws_zone_mute(hub: ProAudioHub, msg):
    await hub.zone_mute(msg["zones"], msg["mute"])


@_cmd({vol.Required("zones"): ZONES, vol.Required("volume"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))})
async def ws_zone_volume(hub: ProAudioHub, msg):
    await hub.zone_volume(msg["zones"], msg["volume"])


@_cmd({vol.Required("raw"): vol.All(vol.Coerce(int), vol.Range(min=0, max=248))})
async def ws_master_volume(hub: ProAudioHub, msg):
    await hub.master_volume(msg["raw"])


@_cmd({vol.Required("on"): bool})
async def ws_unit_power(hub: ProAudioHub, msg):
    await hub.unit_power(msg["on"])


@_cmd({})
async def ws_refresh(hub: ProAudioHub, msg):
    await hub.refresh()


@_cmd(
    {
        vol.Optional("inputs"): {vol.Coerce(str): vol.Any(str, None)},
        vol.Optional("outputs"): {vol.Coerce(str): vol.Any(str, None)},
        vol.Optional("hidden_inputs"): [vol.Coerce(int)],
        vol.Optional("hidden_outputs"): [vol.Coerce(int)],
    },
    admin=True,
)
async def ws_set_names(hub: ProAudioHub, msg):
    await hub.async_set_names(
        msg.get("inputs"), msg.get("outputs"), msg.get("hidden_inputs"), msg.get("hidden_outputs")
    )


@_cmd({vol.Required("preset"): dict}, admin=True)
async def ws_save_preset(hub: ProAudioHub, msg):
    return await hub.async_save_preset(msg["preset"])


@_cmd({vol.Required("preset_id"): str}, admin=True)
async def ws_delete_preset(hub: ProAudioHub, msg):
    await hub.async_delete_preset(msg["preset_id"])


@_cmd({vol.Required("ids"): [str]}, admin=True)
async def ws_reorder_presets(hub: ProAudioHub, msg):
    await hub.async_reorder_presets(msg["ids"])


@_cmd({vol.Required("preset"): str})
async def ws_apply_preset(hub: ProAudioHub, msg):
    await hub.async_apply_preset(msg["preset"])


@_cmd({vol.Required("groups"): [dict]}, admin=True)
async def ws_save_groups(hub: ProAudioHub, msg):
    return await hub.async_save_groups(msg["groups"])
