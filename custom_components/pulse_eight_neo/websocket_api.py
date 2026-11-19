"""WebSocket API for the neo panel (mirrors the ProAudio panel API)."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .hub import NeoHub

NUMS = vol.All([vol.Coerce(int)], vol.Length(min=1))


def _hubs(hass) -> dict[str, NeoHub]:
    return {e.entry_id: e.runtime_data for e in hass.config_entries.async_loaded_entries(DOMAIN) if getattr(e, "runtime_data", None)}


def _hub(hass, eid) -> NeoHub:
    if (h := _hubs(hass).get(eid)) is None:
        raise HomeAssistantError(f"neo matrix {eid} not loaded")
    return h


@callback
def async_register(hass: HomeAssistant) -> None:
    for h in (ws_list_units, ws_subscribe, ws_route, ws_audio_route, ws_cec_power, ws_cec_key, ws_rename, ws_set_hidden,
              ws_save_groups, ws_save_preset, ws_delete_preset, ws_apply_preset, ws_refresh, ws_set_edid):
        websocket_api.async_register_command(hass, h)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list_units"})
@callback
def ws_list_units(hass, conn, msg):
    conn.send_result(msg["id"], [{"entry_id": k, "title": h.title, "model": h.model_name} for k, h in _hubs(hass).items()])


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe", vol.Required("entry_id"): str})
@callback
def ws_subscribe(hass, conn, msg):
    try:
        hub = _hub(hass, msg["entry_id"])
    except HomeAssistantError as err:
        conn.send_error(msg["id"], "not_found", str(err))
        return
    pend = {"h": None}

    @callback
    def send():
        pend["h"] = None
        conn.send_message(websocket_api.event_message(msg["id"], hub.snapshot()))

    @callback
    def changed():
        if pend["h"] is None:
            pend["h"] = hass.loop.call_later(0.1, send)

    unsub = hub.add_listener(changed)

    @callback
    def cancel():
        unsub()
        if pend["h"]:
            pend["h"].cancel()

    conn.subscriptions[msg["id"]] = cancel
    conn.send_result(msg["id"])
    send()


def _cmd(schema: dict, *, admin: bool = False):
    def deco(func):
        async def handler(hass, conn, msg):
            try:
                res = await func(_hub(hass, msg["entry_id"]), msg)
            except HomeAssistantError as err:
                conn.send_error(msg["id"], "neo_error", str(err))
                return
            conn.send_result(msg["id"], res)

        h = websocket_api.async_response(handler)
        if admin:
            h = websocket_api.require_admin(h)
        return websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/{func.__name__.removeprefix('ws_')}",
                                                vol.Required("entry_id"): str, **schema})(h)
    return deco


# numbers from the panel are 1-based (outputs = "zones", inputs = "source")
@_cmd({vol.Required("zones"): NUMS, vol.Required("source"): vol.Coerce(int), vol.Optional("power_on", default=False): bool})
async def ws_route(hub, msg):
    await hub.route([z - 1 for z in msg["zones"]], msg["source"] - 1, power_on=msg["power_on"])


@_cmd({vol.Required("zones"): NUMS, vol.Required("source"): vol.Coerce(int)})
async def ws_audio_route(hub, msg):
    await hub.audio_route([z - 1 for z in msg["zones"]], msg["source"] - 1)


@_cmd({vol.Required("zones"): NUMS, vol.Required("on"): bool})
async def ws_cec_power(hub, msg):
    await hub.cec_power("Output", [z - 1 for z in msg["zones"]], msg["on"])


@_cmd({vol.Required("zones"): NUMS, vol.Required("code"): vol.Coerce(int)})
async def ws_cec_key(hub, msg):
    for z in msg["zones"]:
        await hub.cec_key("Output", z - 1, msg["code"])


@_cmd({vol.Required("mode"): vol.In(["Input", "Output"]), vol.Required("number"): vol.Coerce(int), vol.Required("name"): str}, admin=True)
async def ws_rename(hub, msg):
    await hub.rename(msg["mode"], msg["number"] - 1, msg["name"])


@_cmd({vol.Required("number"): vol.Coerce(int), vol.Required("profile"): vol.Coerce(int)}, admin=True)
async def ws_set_edid(hub, msg):
    await hub.set_edid(msg["number"] - 1, msg["profile"])


@_cmd({vol.Optional("hidden_inputs"): [vol.Coerce(int)], vol.Optional("hidden_outputs"): [vol.Coerce(int)]}, admin=True)
async def ws_set_hidden(hub, msg):
    await hub.set_hidden(msg.get("hidden_inputs"), msg.get("hidden_outputs"))


@_cmd({vol.Required("groups"): [dict]}, admin=True)
async def ws_save_groups(hub, msg):
    return await hub.save_groups(msg["groups"])


@_cmd({vol.Required("preset"): dict}, admin=True)
async def ws_save_preset(hub, msg):
    return await hub.save_preset(msg["preset"])


@_cmd({vol.Required("preset_id"): str}, admin=True)
async def ws_delete_preset(hub, msg):
    await hub.delete_preset(msg["preset_id"])


@_cmd({vol.Required("preset"): str})
async def ws_apply_preset(hub, msg):
    await hub.apply_preset(msg["preset"])


@_cmd({})
async def ws_refresh(hub, msg):
    await hub.refresh_details()
