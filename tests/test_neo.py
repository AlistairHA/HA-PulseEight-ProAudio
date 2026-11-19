from __future__ import annotations

import asyncio

import pytest

from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.pulse_eight_neo.client import link_quality
from custom_components.pulse_eight_neo.const import DOMAIN

SERIAL = "P8SN0123456"


def eid(hass, platform, key):
    e = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{SERIAL}_{key}")
    assert e, key
    return e


async def settle(hass, t=0.3):
    await asyncio.sleep(t)
    await hass.async_block_till_done()


def test_link_quality_rule():
    assert link_quality({"ChannelA": -21, "ChannelB": -22, "ChannelC": -20.5, "ChannelD": -21.5})["rating"] == "good"
    assert link_quality({"ChannelA": -14, "ChannelB": -22, "ChannelC": -20.5, "ChannelD": -21.5})["rating"] == "poor"  # > -15 dB
    assert link_quality({"ChannelA": -25, "ChannelB": -20, "ChannelC": -21, "ChannelD": -21})["rating"] == "poor"  # spread > 3 dB
    assert link_quality(None) is None


async def test_setup_devices_entities(hass, fake, loaded):
    assert loaded.state is ConfigEntryState.LOADED
    reg = dr.async_get(hass)
    unit = reg.async_get_device(identifiers={(DOMAIN, SERIAL)})
    assert unit.model == "neo:X+" and unit.model_id == "FF88SA" and unit.sw_version == "4.12.3" and unit.hw_version == "3"
    outs = [d for d in dr.async_entries_for_config_entry(reg, loaded.entry_id) if d.via_device_id == unit.id]
    assert sorted(d.name for d in outs)[:2] == ["Bar TV", "Cinema AVR"] and len(outs) == 10
    lounge = hass.states.get(eid(hass, "media_player", "out0_player"))
    assert lounge.name == "Lounge TV" and lounge.state == "on" and lounge.attributes["source"] == "Sky Q"
    assert len(lounge.attributes["source_list"]) == 8  # video inputs only; audio inputs 9-12 excluded
    assert hass.states.get(eid(hass, "media_player", "out2_player")).state == "off"  # DPS 1 = standby
    assert hass.states.get(eid(hass, "sensor", "out0_link_quality")).state == "good"
    assert hass.states.get(eid(hass, "sensor", "out3_link_quality")).state == "poor"   # channel A -14.2 dB
    assert float(hass.states.get(eid(hass, "sensor", "out2_cable_length")).state) == 31
    assert hass.states.get(eid(hass, "binary_sensor", "out6_linked")).state == "off"
    assert hass.states.get(eid(hass, "sensor", "out0_link_status")).attributes["receiver_firmware"] == "1.9.2"
    assert hass.states.get(eid(hass, "binary_sensor", "in6_signal")).state == "off"
    assert hass.states.get(eid(hass, "sensor", "status")).state == "System Healthy"
    assert len([e for e in er.async_entries_for_config_entry(er.async_get(hass), loaded.entry_id) if e.unique_id.startswith(f"{SERIAL}_temperature_")]) == 5
    with pytest.raises(AssertionError):
        eid(hass, "sensor", "out8_link_quality")  # HDMI outputs have no HDBaseT sensors


async def test_route_and_cec(hass, fake, loaded):
    e = eid(hass, "media_player", "out1_player")
    await hass.services.async_call("media_player", "select_source", {"entity_id": e, "source": "Blu-ray"}, blocking=True)
    assert fake.outputs[1]["src"] == 3
    await hass.services.async_call("media_player", "turn_off", {"entity_id": e}, blocking=True)
    assert ("GET", "CEC/off/Output/1", None) in fake.calls
    await settle(hass)
    await hass.services.async_call(DOMAIN, "route", {"outputs": ["Gym", 5], "input": "Xbox", "power_on": True}, blocking=True)
    assert fake.outputs[3]["src"] == 4 and fake.outputs[4]["src"] == 4
    assert ("GET", "CEC/on/Output/3", None) in fake.calls
    await hass.services.async_call(DOMAIN, "cec_key", {"outputs": [1], "key": "volume_up"}, blocking=True)
    assert ("POST", "cec/key/Output/0", {"Code": "0x41"}) in fake.calls
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "route", {"outputs": [1], "input": 10}, blocking=True)  # audio-only input
    res = await hass.services.async_call(DOMAIN, "get_status", {}, blocking=True, return_response=True)
    assert res["outputs"][3] | {} == {**res["outputs"][3], "input": "Xbox"}


async def test_external_change_polled(hass, fake, loaded):
    fake.outputs[0]["src"] = 5
    fake.outputs[0]["name"] = "Family Room"
    loaded.runtime_data.request_refresh()
    await settle(hass, 0.5)
    st = hass.states.get(eid(hass, "media_player", "out0_player"))
    assert st.attributes["source"] == "Fire TV" and st.name == "Family Room"


async def test_panel_ws(hass, fake, loaded, hass_ws_client):
    ws = await hass_ws_client(hass)
    eidx = loaded.entry_id
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe", "entry_id": eidx})
    assert (await ws.receive_json())["success"]
    snap = (await ws.receive_json())["event"]
    assert snap["model"] == "neo:X+" and len(snap["outputs"]) == 10 and len(snap["inputs"]) == 12
    o4 = snap["outputs"][3]
    assert o4["link"]["quality"]["rating"] == "poor" and o4["link"]["cable_m"] == 64 and o4["link"]["receiver"]["Model"] == "neo:Ultra Receiver"
    assert snap["outputs"][8]["kind"] == "hdmi" and snap["outputs"][8]["link"] is None
    assert snap["inputs"][9]["kind"] == "audio" and snap["inputs"][0]["zones"] == [1, 3, 9]
    assert snap["temperatures"]["0"] == 41 and snap["modes"]["sink"] is True

    n = 2

    async def call(typ, **kw):
        nonlocal n
        n += 1
        await ws.send_json({"id": n, "type": f"{DOMAIN}/{typ}", "entry_id": eidx, **kw})
        while (m := await ws.receive_json())["id"] != n or m["type"] != "result":
            pass
        return m

    assert (await call("route", zones=[6, 7], source=8))["success"] and fake.outputs[5]["src"] == 7
    assert (await call("cec_power", zones=[3], on=True))["success"] and fake.outputs[2]["dps"] == 0
    assert (await call("rename", mode="Output", number=4, name="Home Gym"))["success"] and fake.outputs[3]["name"] == "Home Gym"
    assert (await call("rename", mode="Input", number=2, name="Apple TV 4K"))["success"] and fake.inputs[1]["name"] == "Apple TV 4K"
    assert not (await call("route", zones=[1], source=11))["success"]
    p = await call("save_preset", preset={"name": "Movie night", "routes": {"1": 4, "9": 4}, "power_off_others": True})
    assert (await call("apply_preset", preset="movie night"))["success"]
    assert fake.outputs[0]["src"] == 3 and fake.outputs[8]["src"] == 3 and fake.outputs[1]["dps"] == 1
    await settle(hass)
    assert er.async_get(hass).async_get_entity_id("button", DOMAIN, f"{SERIAL}_preset_{p['result']['id']}")
    g = await call("save_groups", groups=[{"name": "Downstairs", "zones": [1, 2, 5]}])
    assert g["result"][0]["zones"] == [1, 2, 5]
    await hass.services.async_call(DOMAIN, "route", {"group": "downstairs", "input": 2}, blocking=True)
    assert [fake.outputs[i]["src"] for i in (0, 1, 4)] == [1, 1, 1]


@pytest.mark.parametrize("fake_kwargs", [{"password": "s3cret"}])
async def test_password_login(hass, fake, loaded):
    assert loaded.state is ConfigEntryState.LOADED
    assert fake.calls[0][:2] == ("POST", "Account/Login")


@pytest.mark.parametrize("fake_kwargs", [{"password": "s3cret"}])
async def test_config_flow_auth(hass, fake):
    r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": f"127.0.0.1:{fake.port}", "password": "wrong"})
    assert r["errors"] == {"base": "invalid_auth"}
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"host": f"127.0.0.1:{fake.port}", "password": "s3cret"})
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["title"] == "neo:X+" and r["result"].unique_id == SERIAL
    await hass.async_block_till_done()
    await hass.config_entries.async_unload(r["result"].entry_id)


async def test_offline_then_recovers(hass, fake, loaded):
    e = eid(hass, "media_player", "out0_player")
    fake.online = False
    loaded.runtime_data.request_refresh()
    await settle(hass, 0.4)
    assert hass.states.get(e).state == "unavailable"
    fake.online = True
    loaded.runtime_data.request_refresh()
    await settle(hass, 0.6)
    assert hass.states.get(e).state == "on"


async def test_documented_api_extras(hass, fake, loaded):
    """Routing via Port/List/Concise, HDBT-TX* types, Mirror ports, CEC/Volume, status LEDs."""
    hub = loaded.runtime_data
    assert "ReceiveFrom" not in hub.outputs[0] and hub.concise["Output1"] == 0
    snap = hub.snapshot()
    assert snap["outputs"][0]["kind"] == "hdbt" and snap["outputs"][0]["hdbt_variant"] == "pro"
    assert snap["outputs"][6]["hdbt_variant"] == "lite" and snap["outputs"][8]["kind"] == "hdmi"
    assert snap["mirrors"] == [{"bay": 1, "name": "Rack monitor", "type": "HDMI", "source": 1, "tv_power": None}]
    assert snap["monitoring"] == {"last_contact_s": 600, "installer_id": "1234"}
    assert len(snap["outputs"]) == 10  # mirror isn't counted as an output
    e = eid(hass, "media_player", "out1_player")
    await hass.services.async_call("media_player", "volume_up", {"entity_id": e}, blocking=True)
    await hass.services.async_call("media_player", "volume_mute", {"entity_id": e, "is_volume_muted": True}, blocking=True)
    assert ("GET", "CEC/Volume/Up/Output/1", None) in fake.calls and ("GET", "CEC/Volume/Mute/Output/1", None) in fake.calls
    await hass.services.async_call(DOMAIN, "cec_volume", {"outputs": [3], "action": "down"}, blocking=True)
    assert ("GET", "CEC/Volume/Down/Output/2", None) in fake.calls
    led = eid(hass, "switch", "status_led")
    assert hass.states.get(led).state == "on"
    await hass.services.async_call("switch", "turn_off", {"entity_id": led}, blocking=True)
    assert fake.status_led == "off" and hass.states.get(led).state == "off"
    # routing change made elsewhere shows up via Concise
    fake.outputs[2]["src"] = 6
    hub.request_refresh()
    await settle(hass, 0.5)
    assert hub.source_of(2) == 6 and hub.snapshot()["outputs"][2]["source"] == 7


@pytest.mark.parametrize("fake_kwargs", [{"receive_from": True}])
async def test_legacy_receive_from(hass, fake, loaded):
    hub = loaded.runtime_data
    assert hub.concise == {} and not any(c[1] == "Port/List/Concise" for c in fake.calls)
    assert hub.source_of(4) == 2


async def test_matrix_settings_and_restrictions(hass, fake, loaded):
    """EDID, backlight, CEC options, IR profiles, PSU, AllowedSources, embedded receiver details."""
    hub = loaded.runtime_data
    # PSU sensors
    v12 = hass.states.get(eid(hass, "sensor", "psu_0"))
    assert float(v12.state) == 12.08 and v12.attributes["unit_of_measurement"] == "V"
    # EDID per input
    edid = eid(hass, "select", "in3_edid")
    assert hass.states.get(edid).state == "Dynamic"
    assert "HDR10 7.1" in hass.states.get(edid).attributes["options"]
    assert "Copy output 1: Lounge TV" in hass.states.get(edid).attributes["options"]
    await hass.services.async_call("select", "select_option", {"entity_id": edid, "option": "Ultra HD 4K 7.1"}, blocking=True)
    assert fake.edid[3] == 6 and ("GET", "Port/EDID/Set/6/3", None) in fake.calls
    await hass.services.async_call("select", "select_option", {"entity_id": edid, "option": "Copy output 2: Kitchen TV"}, blocking=True)
    assert fake.edid[3] == 102
    # backlight + CEC options
    bl = eid(hass, "select", "backlight")
    await hass.services.async_call("select", "select_option", {"entity_id": bl, "option": "auto"}, blocking=True)
    assert fake.backlight == "auto" and hass.states.get(bl).state == "auto"
    for key, attr in (("cec_opt_cec_switching", "cec_switching"), ("cec_opt_autopause", "autopause"), ("cec_opt_combokeys", "combokeys"), ("cec_opt_cec", "cec_enabled")):
        sw = eid(hass, "switch", key)
        before = getattr(fake, attr)
        await hass.services.async_call("switch", "turn_off" if before else "turn_on", {"entity_id": sw}, blocking=True)
        assert getattr(fake, attr) is (not before), key
    # IR profile (disabled by default) via hub
    await hub.set_ir_profile(2, 3)
    assert fake.ir[2] == 3
    # AllowedSources: Garden Room (output 8) only takes Sky Q / Apple TV / Fire TV / Chromecast
    garden = hass.states.get(eid(hass, "media_player", "out7_player"))
    assert set(garden.attributes.get("source_list", hub.allowed_sources(7) and [])) <= {"Sky Q", "Apple TV", "Fire TV", "Chromecast"} or garden.state == "off"
    assert [hub.input_name(b) for b in hub.video_input_bays() if hub.source_allowed(7, b)] == ["Sky Q", "Apple TV", "Fire TV", "Chromecast"]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "route", {"outputs": [8], "input": "Xbox"}, blocking=True)
    assert hub.snapshot()["outputs"][7]["allowed_sources"] == [1, 2, 6, 8]
    # remote: display + source key presses
    await hass.services.async_call("remote", "send_command", {"entity_id": eid(hass, "remote", "out0_remote"), "command": ["up", "select", "0x44"]}, blocking=True)
    assert [c[2] for c in fake.calls if c[1] == "cec/key/Output/0"][-3:] == [{"Code": "0x01"}, {"Code": "0x00"}, {"Code": "0x44"}]
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("remote", "send_command", {"entity_id": eid(hass, "remote", "out0_remote"), "command": ["warp_speed"]}, blocking=True)
    await hub.cec_key("Input", 0, 0x44)
    assert ("POST", "cec/key/Input/0", {"Code": "0x44"}) in fake.calls


@pytest.fixture
def udp_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_udp_push(hass, fake, udp_port):
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.pulse_eight_neo.udp import decode
    pkts = fake.udp_state()
    assert decode(pkts[1])["ports"][12]["route"] == 0 and decode(pkts[0])["identity"]["serial"] == SERIAL
    await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, title="neo:X+", unique_id=SERIAL, data={"host": f"127.0.0.1:{fake.port}", "password": ""},
                            options={"udp_push": True, "udp_port": udp_port, "scan_interval": 120})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hub = entry.runtime_data
    # change state on the "matrix" without HA polling; only the UDP push tells HA
    fake.outputs[0]["src"] = 5
    fake.outputs[2]["dps"] = 0
    fake.inputs[1]["signal"] = False
    fake.send_udp(udp_port)
    await settle(hass, 0.6)
    assert hub.udp_active and hub.udp_packets >= 3
    assert hass.states.get(eid(hass, "media_player", "out0_player")).attributes["source"] == "Fire TV"
    assert hass.states.get(eid(hass, "media_player", "out2_player")).state == "on"
    assert hass.states.get(eid(hass, "binary_sensor", "in1_signal")).state == "off"
    assert hub.health["Temperature0"] == 40
    # packets from elsewhere are ignored
    from custom_components.pulse_eight_neo.udp import encode, encode_port
    import socket
    bad = encode(2, encode_port("output", 0, index=12, route=3), sender=b"P8\x01\x00XXXX")
    hub._host_ips = {"10.9.9.9"}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sk:
        sk.sendto(bad, ("127.0.0.1", udp_port))
    await settle(hass, 0.5)
    assert hub.source_of(0) == 5
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_dhcp_discovery(hass, fake):
    from homeassistant.config_entries import SOURCE_DHCP
    from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
    from unittest.mock import patch
    import custom_components.pulse_eight_neo.config_flow as cf
    real = cf.NeoClient
    with patch.object(cf, "NeoClient", lambda host, pw="", **kw: real(f"127.0.0.1:{fake.port}", pw, **kw)):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_DHCP},
                                                      data=DhcpServiceInfo(ip="192.168.1.70", hostname="p8sn0123456", macaddress="001582123456"))
        assert r["type"] is FlowResultType.FORM and r["step_id"] == "discovery_confirm"
        with patch("custom_components.pulse_eight_neo.async_setup_entry", return_value=True):
            r = await hass.config_entries.flow.async_configure(r["flow_id"], {"password": ""})
            await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY and r["data"]["host"] == "192.168.1.70" and r["title"] == "neo:X+"
    # a ProAmp8 shares the MAC prefix: not offered
    fake.model = "PROAMP8"
    with patch.object(cf, "NeoClient", lambda host, pw="", **kw: real(f"127.0.0.1:{fake.port}", pw, **kw)):
        r = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_DHCP},
                                                      data=DhcpServiceInfo(ip="192.168.1.71", hostname="p8sn0999", macaddress="001582999999"))
    assert r["type"] is FlowResultType.ABORT and r["reason"] in ("not_neo", "already_configured")
