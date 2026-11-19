"""ProAudio integration tests (real TCP to a fake unit)."""

from __future__ import annotations

import asyncio

import pytest

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.pulse_eight_proaudio.client import build_inputs, model_spec, parse_frames, zone_spec
from custom_components.pulse_eight_proaudio.const import DOMAIN

SERIAL = "59B2S12345678"


async def settle(hass, t=0.4):
    await asyncio.sleep(t)
    await hass.async_block_till_done()


def mp(hass, zone):
    return er.async_get(hass).async_get_entity_id("media_player", DOMAIN, f"{SERIAL}_zone{zone}")


# ---- pure protocol helpers ---------------------------------------------------

def test_helpers():
    assert zone_spec([5, 1, 2, 3, 8]) == "@1:3@5@8"
    assert parse_frames("x^+$\r\n^=SZ.2 @001,003$^=MV 1")[0] == ["+", "=SZ.2 @001,003"]
    pa16_native = [i.source for i in build_inputs(model_spec("ProAudio16"), False)]
    pa16_xio = [i.source for i in build_inputs(model_spec("ProAudio16"), True)]
    assert pa16_native[16] == 17 and pa16_xio[16] == 33 and pa16_xio[-1] == 80
    pa32 = build_inputs(model_spec("ProAudio32"), False)
    assert len(pa32) == 80 and pa32[32].kind == "coax" and pa32[32].source == 33 and pa32[64].source == 65


# ---- setup / entities ---------------------------------------------------------

async def test_setup_entities(hass: HomeAssistant, fake, loaded):
    assert loaded.state is ConfigEntryState.LOADED
    devreg = dr.async_get(hass)
    unit = devreg.async_get_device(identifiers={(DOMAIN, SERIAL)})
    assert unit.model == "ProAudio32" and unit.sw_version == "1.23a"
    zones = [d for d in dr.async_entries_for_config_entry(devreg, loaded.entry_id) if d.via_device_id == unit.id]
    assert len(zones) == 32

    z1 = hass.states.get(mp(hass, 1))
    assert z1.state == "on" and z1.attributes["source"] == "Analog 1"
    assert z1.attributes["volume_level"] == 0.4
    assert len(z1.attributes["source_list"]) == 80
    assert hass.states.get(mp(hass, 3)).attributes["source"] == "Coax 1"
    assert hass.states.get(mp(hass, 20)).state == "off"
    ent = er.async_get(hass)
    master = ent.async_get_entity_id("number", DOMAIN, f"{SERIAL}_master_volume")
    assert hass.states.get(master).state == "0.0"
    conn = ent.async_get_entity_id("binary_sensor", DOMAIN, f"{SERIAL}_connected")
    assert hass.states.get(conn).state == "on"
    ip = ent.async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_ip_address")
    assert hass.states.get(ip).state == "192.168.1.60"
    assert "proaudio" in hass.data["frontend_panels"]


async def test_media_player_controls(hass, fake, loaded):
    e = mp(hass, 5)
    await hass.services.async_call("media_player", "select_source", {"entity_id": e, "source": "Optical 2"}, blocking=True)
    await hass.services.async_call("media_player", "volume_set", {"entity_id": e, "volume_level": 0.65}, blocking=True)
    await hass.services.async_call("media_player", "volume_mute", {"entity_id": e, "is_volume_muted": True}, blocking=True)
    await hass.services.async_call("media_player", "turn_off", {"entity_id": e}, blocking=True)
    await settle(hass)
    assert fake.state[5] == {**fake.state[5], "SZ": 66, "VPZ": 65, "VMZ": 1, "PZ": 0}
    st = hass.states.get(e)
    assert st.state == "off"
    await hass.services.async_call("media_player", "turn_on", {"entity_id": e}, blocking=True)
    await settle(hass)
    assert hass.states.get(e).attributes["source"] == "Optical 2"


async def test_external_change_pushed(hass, fake, loaded):
    r, w = await asyncio.open_connection("127.0.0.1", fake.port)
    w.write(b"^PZ @10,1$^SZ @10,7$^VPZ @10,90$")
    await w.drain()
    await settle(hass)
    st = hass.states.get(mp(hass, 10))
    assert st.attributes["source"] == "Analog 7" and st.attributes["volume_level"] == 0.9
    w.close()


async def test_services_and_errors(hass, fake, loaded):
    await hass.services.async_call(DOMAIN, "route", {"zones": [1, 2, 3], "source": "Analog 9"}, blocking=True)
    assert [fake.state[z]["SZ"] for z in (1, 2, 3)] == [9, 9, 9]
    await hass.services.async_call(DOMAIN, "zone_volume", {"zones": [1, 2], "volume": 12}, blocking=True)
    assert fake.state[2]["VPZ"] == 12
    await hass.services.async_call(DOMAIN, "clear_all", {}, blocking=True)
    assert all(v["SZ"] == 0 for v in fake.state.values())
    res = await hass.services.async_call(DOMAIN, "send_command", {"command": "^SZ @1,99$"}, blocking=True, return_response=True)
    assert res == {"error_code": 2}
    from homeassistant.exceptions import ServiceValidationError
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "route", {"zones": [40], "source": 1}, blocking=True)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "send_command", {"command": "FS 65535"}, blocking=True)
    await settle(hass)
    ent = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{SERIAL}_last_error")
    assert hass.states.get(ent).state.startswith("2:")


async def test_websocket_panel_api(hass, fake, loaded, hass_ws_client):
    ws = await hass_ws_client(hass)
    eid = loaded.entry_id
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/list_units"})
    assert (await ws.receive_json())["result"][0]["entry_id"] == eid

    await ws.send_json({"id": 2, "type": f"{DOMAIN}/subscribe", "entry_id": eid})
    assert (await ws.receive_json())["success"]
    snap = (await ws.receive_json())["event"]
    assert snap["model"] == "ProAudio32" and len(snap["outputs"]) == 32 and len(snap["inputs"]) == 80
    coax1 = next(i for i in snap["inputs"] if i["source"] == 33)
    assert coax1["zones"] == [3] and coax1["signal"] == "pcm"
    opt1 = next(i for i in snap["inputs"] if i["source"] == 65)
    assert opt1["signal"] == "encoded"

    async def call(i, typ, **kw):
        await ws.send_json({"id": i, "type": f"{DOMAIN}/{typ}", "entry_id": eid, **kw})
        while True:
            msg = await ws.receive_json()
            if msg["id"] == i and msg["type"] == "result":
                return msg

    assert (await call(3, "route", zones=[11, 12, 13], source=2))["success"]
    assert [fake.state[z]["SZ"] for z in (11, 12, 13)] == [2, 2, 2]
    assert (await call(4, "zone_power", zones=[11, 12], on=True))["success"]
    assert (await call(5, "zone_mute", zones=[11], mute=True))["success"]
    assert (await call(6, "master_volume", raw=180))["success"] and fake.master == 180
    err = await call(7, "route", zones=[99], source=1)
    assert not err["success"] and err["error"]["code"] == "proaudio_error"

    assert (await call(8, "set_names", inputs={"1": "AMB Source", "33": "TV"}, outputs={"1": "Kitchen", "2": "Master Bedroom"}, hidden_inputs=[80]))["success"]
    await settle(hass)
    assert hass.states.get(mp(hass, 1)).name == "Kitchen"
    assert "AMB Source" in hass.states.get(mp(hass, 2)).attributes["source_list"]
    dev = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, f"{SERIAL}_zone2")})
    assert dev.name == "Master Bedroom"

    saved = await call(9, "save_preset", preset={"name": "Whole house", "routes": {str(z): 1 for z in range(1, 9)}, "volume": 30, "disconnect_others": True})
    pid = saved["result"]["id"]
    await call(10, "save_preset", preset={"name": "Master bedroom", "routes": {"2": 1}})
    await settle(hass)
    btn = er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{SERIAL}_preset_{pid}")
    assert hass.states.get(btn).name.endswith("Preset Whole house")

    assert (await call(20, "route", zones=[20], source=1))["success"]  # on AMB but not in preset
    await hass.services.async_call("button", "press", {"entity_id": btn}, blocking=True)
    assert all(fake.state[z]["SZ"] == 1 and fake.state[z]["PZ"] == 1 and fake.state[z]["VPZ"] == 30 for z in range(1, 9))
    assert fake.state[20]["SZ"] == 0
    assert (await call(21, "clear_all"))["success"]
    assert (await call(22, "apply_preset", preset="master bedroom"))["success"]
    assert fake.state[2]["SZ"] == 1 and fake.state[1]["SZ"] == 0

    assert (await call(23, "delete_preset", preset_id=pid))["success"]
    await settle(hass)
    assert er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{SERIAL}_preset_{pid}") is None


async def test_reconnect(hass, fake, loaded):
    e = mp(hass, 1)
    await fake.drop_clients()
    await settle(hass, 0.3)
    assert hass.states.get(e).state == "unavailable"
    await settle(hass, 3.0)
    assert hass.states.get(e).state == "on"


@pytest.mark.parametrize("fake_kwargs", [{"ack": False, "breakaway": True}])
async def test_ack_off_and_breakaway(hass, fake, loaded):
    e = mp(hass, 6)
    st = hass.states.get(e)
    assert st.state == "on", st
    assert st.attributes["source"] == "Analog 6"
    await hass.services.async_call("media_player", "select_source", {"entity_id": e, "source": "Analog 3"}, blocking=True)
    assert fake.state[6]["SZ"] == 3
    from homeassistant.exceptions import HomeAssistantError
    with pytest.raises(HomeAssistantError):  # error detected even without ACKs
        await hass.services.async_call(DOMAIN, "route", {"zones": [1], "source": 120}, blocking=True)


async def test_config_flow(hass, fake):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": "127.0.0.1", "port": fake.port})
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["title"] == "ProAudio32"
    assert r["result"].unique_id == SERIAL
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(r["result"].entry_id)


async def test_config_flow_cannot_connect(hass, fake):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": "127.0.0.1", "port": 1})
    assert r["errors"] == {"base": "cannot_connect"}


async def test_zone_groups(hass, fake, loaded, hass_ws_client):
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/save_groups", "entry_id": loaded.entry_id,
                        "groups": [{"name": "Upstairs", "zones": [2, 9, 10]}, {"name": "Outside", "zones": [6, 2, 99]}, {"name": " ", "zones": [1]}]})
    res = (await ws.receive_json())["result"]
    assert [g["name"] for g in res] == ["Upstairs", "Outside"]
    assert res[1]["zones"] == [6]  # zone 2 already in Upstairs, 99 out of range
    await hass.services.async_call(DOMAIN, "route", {"group": "upstairs", "source": 4}, blocking=True)
    assert [fake.state[z]["SZ"] for z in (2, 9, 10)] == [4, 4, 4]
    await hass.services.async_call(DOMAIN, "zone_mute", {"group": "Outside", "zones": [1], "mute": True}, blocking=True)
    assert fake.state[6]["VMZ"] == 1 and fake.state[1]["VMZ"] == 1
    assert loaded.runtime_data.snapshot()["groups"][0]["name"] == "Upstairs"


async def test_preset_same_name_updates(hass, fake, loaded):
    hub = loaded.runtime_data
    a = await hub.async_save_preset({"name": "Party", "routes": {"1": 2}})
    b = await hub.async_save_preset({"name": "party", "routes": {"2": 3}})
    assert a["id"] == b["id"] and len(hub.presets) == 1 and hub.presets[0]["routes"] == {"2": 3}
