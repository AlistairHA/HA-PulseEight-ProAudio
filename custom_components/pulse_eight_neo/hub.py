"""Hub for one neo matrix: polling, normalised state, presets/groups, panel snapshot."""

from __future__ import annotations

import asyncio
import socket
from collections import deque
from collections.abc import Callable
import logging
import time
from typing import Any
import uuid

from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from .client import (
    BACKLIGHT_OPTIONS,
    CEC_KEYS,
    EDID_CLONE_BASE,
    EDID_HDR,
    EDID_PROFILES,
    CEC_POWER,
    MODELS,
    NeoApiError,
    NeoAuthError,
    NeoClient,
    NeoConnectionError,
    NeoNotFound,
    NeoError,
    as_bool,
    as_int,
    first,
    link_quality,
)
from .const import DOMAIN, SIGNAL_SETTINGS

_LOGGER = logging.getLogger(__name__)


def _defaults() -> dict[str, Any]:
    return {"hidden_inputs": [], "hidden_outputs": [], "presets": [], "groups": []}


class NeoHub:
    def __init__(self, hass: HomeAssistant, entry_id: str, title: str, client: NeoClient,
                 *, fast: float = 5, slow: float = 60) -> None:
        self.hass, self.entry_id, self.title, self.client = hass, entry_id, title, client
        self.fast, self.slow = fast, slow
        self.details: dict = {}
        self.features: dict = {}
        self.health: dict = {}
        self.modes: dict = {}
        self.inputs: dict[int, dict] = {}
        self.outputs: dict[int, dict] = {}
        self.mirrors: dict[int, dict] = {}
        self.concise: dict[str, int] = {}
        self.monitoring: dict = {}
        self.cec_settings: dict[str, dict | None] = {}
        self.ir_profiles: list[dict] = []
        self.ir_details: dict[int, dict] = {}
        self._unsupported: set[str] = set()
        # UDP push
        self.last_udp: float | None = None
        self.udp_packets = 0
        self._udp_unsub: Callable[[], None] | None = None
        self._udp_senders: set[bytes] = set()
        self._host_ips: set[str] = set()
        self._fire_handle: asyncio.TimerHandle | None = None
        self.out_details: dict[int, dict] = {}
        self.in_details: dict[int, dict] = {}
        self.remote: dict[int, dict | None] = {}
        self.connected = False
        self.auth_error = False
        self.last_update: float | None = None
        self.last_detail: float | None = None
        self.errors: deque = deque(maxlen=25)
        self.settings: dict[str, Any] = _defaults()
        self._store: Store = Store(hass, 1, f"{DOMAIN}.{entry_id}")
        self._listeners: list[Callable[[], None]] = []
        self._task: asyncio.Task | None = None
        self._wake = asyncio.Event()

    # ---- lifecycle -------------------------------------------------------------
    async def async_load(self) -> None:
        if data := await self._store.async_load():
            self.settings = {**_defaults(), **data}

    async def async_save(self) -> None:
        await self._store.async_save(self.settings)

    async def first_refresh(self) -> None:
        await self._poll(full=True)

    def start(self) -> None:
        self._task = self.hass.async_create_background_task(self._loop(), f"{DOMAIN}-{self.entry_id}")

    async def start_udp(self, port: int) -> bool:
        """Listen for the matrix's state broadcasts. Returns False if the port can't be opened."""
        from .udp import UdpListener  # noqa: PLC0415
        host = self.client.host.rsplit(":", 1)[0] if self.client.host.count(":") == 1 else self.client.host
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, 80, type=socket.SOCK_DGRAM)
            self._host_ips = {i[4][0] for i in infos}
        except OSError:
            self._host_ips = {host}
        try:
            self._udp_unsub = await UdpListener.subscribe(port, self._udp_accepts, self._udp_packet)
        except OSError as err:
            _LOGGER.warning("neo: can't listen for UDP state broadcasts on port %s (%s); polling only", port, err)
            return False
        return True

    def _udp_accepts(self, ip: str, pkt: dict) -> bool:
        if pkt["type"] == 0 and self.serial and pkt["identity"]["serial"] == self.serial:
            self._udp_senders.add(pkt["sender"])
            return True
        return ip in self._host_ips or pkt["sender"] in self._udp_senders

    @callback
    def _udp_packet(self, pkt: dict) -> None:
        self.last_udp = time.time()
        self.udp_packets += 1
        if pkt["type"] == 2:
            for r in pkt["ports"]:
                bay = r["bay"]
                target = self.outputs.get(bay) if r["mode"] == "output" else self.inputs.get(bay) if r["mode"] == "input" else None
                if target is None:
                    continue
                target["HasSignal"], target["HPD"] = r["signal"], r["hpd"]
                if r["name"]:
                    target["Name"] = r["name"]
                if r["mode"] == "output":
                    if r["route"] is not None:
                        target["ReceiveFrom"] = r["route"]
                        if f"Output{bay + 1}" in self.concise:
                            self.concise[f"Output{bay + 1}"] = r["route"]
                    if r["dps"] is not None:
                        target["DPS"] = r["dps"]
        elif pkt["type"] == 21:
            for i, t in enumerate(pkt["temperatures"]):
                self.health[f"Temperature{i}"] = t
        # coalesce bursts: at most 4 UI updates a second
        if self._fire_handle is None:
            def _go() -> None:
                self._fire_handle = None
                self._fire()
            self._fire_handle = asyncio.get_running_loop().call_later(0.25, _go)

    @property
    def udp_active(self) -> bool:
        return self.last_udp is not None and time.time() - self.last_udp < 90

    async def stop(self) -> None:
        if self._udp_unsub:
            self._udp_unsub()
            self._udp_unsub = None
        if self._fire_handle:
            self._fire_handle.cancel()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        await self.client.close()

    async def _loop(self) -> None:
        while True:
            try:
                # with live UDP pushes, polling is only a safety net
                await asyncio.wait_for(self._wake.wait(), max(self.fast, 30) if self.udp_active else self.fast)
            except TimeoutError:
                pass
            self._wake.clear()
            full = self.last_detail is None or time.time() - self.last_detail >= self.slow
            try:
                await self._poll(full=full)
            except NeoError as err:
                _LOGGER.debug("neo poll failed: %s", err)

    def request_refresh(self) -> None:
        self._wake.set()

    # ---- listeners -------------------------------------------------------------
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb) if cb in self._listeners else None

    @callback
    def _fire(self) -> None:
        for cb in list(self._listeners):
            cb()

    # ---- polling ---------------------------------------------------------------
    async def _poll(self, full: bool) -> None:
        c = self.client
        try:
            if full or not self.details:
                self.details = await c.details()
            ports = await c.ports()
            if full:
                self.health = await c.health()
                try:
                    self.features = await c.features()
                except NeoApiError:
                    self.features = {}
                for key, path in (("sink", "Audio/SinkMode"), ("manual", "Audio/ManualMode"), ("auto_on", "CEC/AutoPowerOn")):
                    self.modes[key] = await c.setting(path)
                self.modes["network"] = await c.setting("Network/Settings")
                self.monitoring = await c.monitoring() or {}
                for key, path in (("autopause", "CEC/AutoPause"), ("combokeys", "CEC/ComboKeys"), ("ir_profiles", "IR/Profiles")):
                    if path in self._unsupported:
                        continue
                    try:
                        self.cec_settings[key] = await c.request(path, check=False)
                    except NeoNotFound:
                        self._unsupported.add(path)
                        self.cec_settings[key] = None
                    except NeoConnectionError:
                        pass
                profiles = first(self.cec_settings.get("ir_profiles"), "Profiles", default=[])
                self.ir_profiles = [x for x in profiles if isinstance(x, dict) and as_int(first(x, "Id")) is not None] if isinstance(profiles, list) else []
        except NeoAuthError:
            self.auth_error = True
            self._mark(False)
            raise
        except NeoError:
            self._mark(False)
            raise
        self.auth_error = False
        inputs: dict[int, dict] = {}
        outputs: dict[int, dict] = {}
        mirrors: dict[int, dict] = {}
        for p in ports:
            bay = as_int(first(p, "Bay"))
            if bay is None:
                continue
            mode = str(first(p, "Mode", default="")).lower()
            {"input": inputs, "output": outputs, "mirror": mirrors}.get(mode, {})[bay] = p
        self.inputs, self.outputs, self.mirrors = inputs, outputs, mirrors
        # Documented Port/List has no routing field on some firmware: use Port/List/Concise then.
        if any("ReceiveFrom" not in p for p in (*outputs.values(), *mirrors.values())):
            try:
                self.concise = await c.concise_routes()
            except NeoError as err:
                _LOGGER.debug("Port/List/Concise: %s", err)
        else:
            self.concise = {}
        if full:
            await self._poll_details()
        self.last_update = time.time()
        self._mark(True)

    async def _poll_details(self) -> None:
        c = self.client
        for bay in sorted(self.outputs):
            try:
                self.out_details[bay] = await c.port_details("Output", bay)
            except NeoError as err:
                _LOGGER.debug("Port/Details Output %s: %s", bay, err)
            embedded = first(self.out_details.get(bay), "RemoteDetails")
            if isinstance(embedded, dict) and embedded:
                self.remote[bay] = embedded  # some firmware includes it in Port/Details
            elif self.is_hdbt(bay) and self._linked(bay) is not False:
                try:
                    self.remote[bay] = await c.remote_details("Output", bay)
                except NeoApiError:
                    self.remote[bay] = None
                except NeoError:
                    pass
            else:
                self.remote[bay] = None
            if self.ir_profiles:
                try:
                    self.ir_details[bay] = await c.request(f"IR/Details/{bay}")
                except NeoError:
                    pass
        for bay in sorted(self.inputs):
            try:
                self.in_details[bay] = await c.port_details("Input", bay)
            except NeoError:
                pass
        self.last_detail = time.time()

    def _mark(self, ok: bool) -> None:
        if self.connected != ok or ok:
            self.connected = ok
            self._fire()

    async def refresh_details(self) -> None:
        await self._run(self._poll(full=True))

    # ---- helpers ---------------------------------------------------------------
    @property
    def model_code(self) -> str:
        return str(first(self.details, "Model", default=""))

    @property
    def model_name(self) -> str:
        return MODELS.get(self.model_code, self.model_code or "neo matrix")

    @property
    def serial(self) -> str | None:
        return first(self.details, "Serial")

    def port_type(self, bay: int) -> str:
        return str(first(self.outputs.get(bay), "Type", default=""))

    def hdbt_variant(self, bay: int) -> str | None:
        """'pro' / 'lite' for HDBT-TXPRO / HDBT-TXLITE outputs (Port/List Type)."""
        t = self.port_type(bay).upper()
        return "pro" if "TXPRO" in t else "lite" if "TXLITE" in t else None

    def is_hdbt(self, bay: int) -> bool:
        t = self.port_type(bay).lower()
        d = self.out_details.get(bay) or {}
        return "hdbt" in t or "hdbaset" in t or "LinkStatus" in d or "LinkQuality" in d

    def _linked(self, bay: int) -> bool | None:
        return as_bool(first(self.out_details.get(bay), "LinkStatus"))

    def input_name(self, bay: int) -> str:
        return str(first(self.inputs.get(bay), "Name", default="") or f"Input {bay + 1}")

    def output_name(self, bay: int) -> str:
        return str(first(self.outputs.get(bay), "Name", default="") or f"Output {bay + 1}")

    def is_audio_input(self, bay: int) -> bool:
        return "audio" in str(first(self.inputs.get(bay), "Type", default="")).lower() or bay >= self.video_inputs

    @property
    def video_inputs(self) -> int:
        n = as_int(first(first(first(self.features, "Video"), "Input"), "Bays"))
        return n if n is not None else len([b for b in self.inputs if "audio" not in str(first(self.inputs[b], "Type", default="")).lower()]) or len(self.inputs)

    def video_input_bays(self) -> list[int]:
        return [b for b in sorted(self.inputs) if not self.is_audio_input(b)]

    def source_of(self, bay: int) -> int | None:
        v = as_int(first(self.outputs.get(bay), "ReceiveFrom"))
        if v is None:
            v = self.concise.get(f"Output{bay + 1}")
        return v if v is not None and v >= 0 else None

    def mirror_source_of(self, bay: int) -> int | None:
        v = as_int(first(self.mirrors.get(bay), "ReceiveFrom"))
        if v is None:
            v = self.concise.get(f"Mirror{bay + 1}")
        return v if v is not None and v >= 0 else None

    def audio_source_of(self, bay: int) -> int | None:
        v = as_int(first(self.outputs.get(bay), "AudioReceived", "AudioRecieved"))
        return v if v is not None and v >= 0 else None

    def allowed_sources(self, bay: int) -> list[int] | None:
        v = first(self.out_details.get(bay), "AllowedSources", default=first(self.outputs.get(bay), "AllowedSources"))
        return [int(x) for x in v if as_int(x) is not None] if isinstance(v, list) else None

    def source_allowed(self, out_bay: int, in_bay: int) -> bool:
        a = self.allowed_sources(out_bay)
        return a is None or in_bay in a

    @property
    def psu(self) -> list[dict]:
        v = first(self.health, "psu", "PSU")
        return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []

    def edid_profile(self, bay: int) -> int | None:
        return as_int(first(self.in_details.get(bay), "EdidProfile", default=first(self.inputs.get(bay), "EdidProfile")))

    def edid_options(self) -> dict[int, str]:
        hdr = bool(first(first(self.features, "Video"), "Scrambling"))
        opts = {k: v for k, v in EDID_PROFILES.items() if hdr or k not in EDID_HDR}
        for b in sorted(self.outputs):
            opts[EDID_CLONE_BASE + b] = f"Copy output {b + 1}: {self.output_name(b)}"
        return opts

    def ir_profile(self, bay: int) -> int | None:
        return as_int(first(self.ir_details.get(bay), "Id"))

    def tv_power(self, bay: int) -> str | None:
        dps = as_int(first(self.outputs.get(bay), "DPS"))
        return CEC_POWER.get(dps) if dps is not None else None

    def input_by_name(self, name: str) -> int:
        s = str(name).strip()
        if s.isdigit():
            return int(s) - 1
        for b in self.inputs:
            if self.input_name(b).casefold() == s.casefold():
                return b
        raise ServiceValidationError(f"Unknown neo input '{name}'")

    def output_by_name(self, name: str | int) -> int:
        s = str(name).strip()
        if s.isdigit():
            return int(s) - 1
        for b in self.outputs:
            if self.output_name(b).casefold() == s.casefold():
                return b
        raise ServiceValidationError(f"Unknown neo output '{name}'")

    # ---- control ---------------------------------------------------------------
    async def _run(self, coro) -> Any:
        try:
            return await coro
        except NeoError as err:
            self.errors.append({"time": time.time(), "message": str(err)})
            self._fire()
            raise HomeAssistantError(f"neo: {err}") from err

    def _check(self, outputs: list[int], input_bay: int | None = None) -> None:
        bad = [o + 1 for o in outputs if o not in self.outputs]
        if bad or not outputs:
            raise ServiceValidationError(f"Invalid output(s) {bad or outputs}")
        if input_bay is not None and input_bay not in self.inputs:
            raise ServiceValidationError(f"Invalid input {input_bay + 1}")
        if input_bay is not None and (blocked := [self.output_name(o) for o in outputs if not self.source_allowed(o, input_bay)]):
            raise ServiceValidationError(f"{self.input_name(input_bay)} isn't allowed on {', '.join(blocked)} (matrix routing restrictions)")

    async def route(self, outputs: list[int], input_bay: int, *, power_on: bool = False) -> None:
        """Route video (and following audio) of input_bay to each output (bays, zero-based)."""
        self._check(outputs, input_bay)
        if self.is_audio_input(input_bay):
            raise ServiceValidationError(f"{self.input_name(input_bay)} is an audio-only input; use audio routing")
        for o in outputs:
            await self._run(self.client.route(input_bay, o))
            self.outputs[o]["ReceiveFrom"] = input_bay
            if f"Output{o + 1}" in self.concise:
                self.concise[f"Output{o + 1}"] = input_bay
            if power_on:
                try:
                    await self.client.cec_power("Output", o, True)
                except NeoError as err:
                    _LOGGER.debug("CEC on after route failed: %s", err)
        self._fire()
        self.request_refresh()

    async def audio_route(self, outputs: list[int], input_bay: int) -> None:
        self._check(outputs, input_bay if input_bay >= 0 else None)
        for o in outputs:
            await self._run(self.client.audio_route(input_bay, o))
            self.outputs[o]["AudioRecieved"] = input_bay
        self._fire()
        self.request_refresh()

    async def cec_power(self, mode: str, bays: list[int], on: bool) -> None:
        for b in bays:
            await self._run(self.client.cec_power(mode, b, on))
            if mode == "Output" and b in self.outputs:
                self.outputs[b]["DPS"] = 2 if on else 3  # transitioning until the next poll
        self._fire()
        self.request_refresh()

    async def cec_key(self, mode: str, bay: int, code: int) -> None:
        await self._run(self.client.cec_key(mode, bay, code))

    async def cec_volume(self, method: str, mode: str, bay: int) -> None:
        """CEC/Volume (Up/Down/Mute) to the TV/AVR on an output or mirror port; falls back to a key press."""
        try:
            await self.client.cec_volume(method, mode, bay)
        except NeoError as err:  # older firmware without CEC/Volume, or AVR not answering
            _LOGGER.debug("CEC/Volume failed (%s); falling back to CEC key", err)
            await self.cec_key(mode, bay, CEC_KEYS[{"Up": "volume_up", "Down": "volume_down", "Mute": "mute"}[method]])
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def set_edid(self, bay: int, profile: int) -> None:
        if bay not in self.inputs:
            raise ServiceValidationError(f"Invalid input {bay + 1}")
        if profile not in self.edid_options() and profile != self.edid_profile(bay):
            raise ServiceValidationError(f"EDID profile {profile} isn't supported on this matrix")
        await self._run(self.client.set_edid(profile, bay))
        self.in_details.setdefault(bay, {})["EdidProfile"] = profile
        self._fire()

    async def set_backlight(self, value: str) -> None:
        if value not in BACKLIGHT_OPTIONS:
            raise ServiceValidationError(f"Backlight must be one of {BACKLIGHT_OPTIONS}")
        await self._run(self.client.set_backlight(value))
        self.features["BacklightLED"] = value
        self._fire()

    async def set_cec_option(self, key: str, on: bool) -> None:
        c = self.client
        fn = {"cec": c.set_cec_enabled, "cec_switching": c.set_cec_switching,
              "autopause": c.set_cec_autopause, "combokeys": c.set_cec_combokeys}[key]
        await self._run(fn(on))
        if key == "cec":
            self.features["CEC"] = on
        elif key == "cec_switching":
            self.features["CEC_Switching"] = on
        elif key == "autopause":
            self.cec_settings["autopause"] = {"AutoPause": on}
        else:
            self.cec_settings["combokeys"] = {"ComboKeys": on}
        self._fire()

    def cec_option(self, key: str) -> bool | None:
        if key == "cec":
            return as_bool(first(self.features, "CEC"))
        if key == "cec_switching":
            return as_bool(first(self.features, "CEC_Switching"))
        if key == "autopause":
            return as_bool(first(self.cec_settings.get("autopause"), "AutoPause"))
        return as_bool(first(self.cec_settings.get("combokeys"), "ComboKeys"))

    async def set_ir_profile(self, bay: int, profile: int) -> None:
        if profile not in {as_int(first(p, "Id")) for p in self.ir_profiles}:
            raise ServiceValidationError(f"Unknown IR profile {profile}")
        await self._run(self.client.set_ir_profile(bay, profile))
        self.ir_details[bay] = {**(self.ir_details.get(bay) or {}), "Id": profile}
        self._fire()

    async def set_status_led(self, on: bool) -> None:
        await self._run(self.client.set_status_led(on))
        self.features["StatusLED"] = "on" if on else "off"
        self._fire()

    async def rename(self, mode: str, bay: int, name: str) -> None:
        name = name.strip()
        if not name:
            raise ServiceValidationError("Name cannot be empty")
        await self._run(self.client.set_name(mode, bay, name))
        (self.outputs if mode == "Output" else self.inputs).setdefault(bay, {})["Name"] = name
        async_dispatcher_send(self.hass, SIGNAL_SETTINGS.format(self.entry_id))
        self._fire()
        self.request_refresh()

    async def restart(self) -> None:
        await self.client.restart()

    # ---- local settings: hidden, groups, presets -------------------------------
    async def set_hidden(self, inputs: list[int] | None, outputs: list[int] | None) -> None:
        if inputs is not None:
            self.settings["hidden_inputs"] = sorted({int(x) for x in inputs})
        if outputs is not None:
            self.settings["hidden_outputs"] = sorted({int(x) for x in outputs})
        await self.async_save()
        self._fire()

    async def save_groups(self, groups: list[dict]) -> list[dict]:
        seen: set[int] = set()
        clean = []
        for g in groups:
            name = str(g.get("name") or "").strip()
            if not name:
                continue
            zones = [int(z) for z in g.get("zones") or [] if 1 <= int(z) <= 64 and int(z) not in seen]
            seen.update(zones)
            clean.append({"id": g.get("id") or uuid.uuid4().hex[:8], "name": name, "zones": sorted(zones)})
        self.settings["groups"] = clean
        await self.async_save()
        self._fire()
        return clean

    def group_outputs(self, key: str) -> list[int]:
        for g in self.settings["groups"]:
            if g["id"] == key or g["name"].casefold() == str(key).casefold():
                return [z - 1 for z in g["zones"]]
        raise ServiceValidationError(f"Unknown output group '{key}'")

    @property
    def presets(self) -> list[dict]:
        return self.settings["presets"]

    def get_preset(self, key: str) -> dict:
        for p in self.presets:
            if p["id"] == key or p["name"].casefold() == str(key).casefold():
                return p
        raise ServiceValidationError(f"Unknown neo preset '{key}'")

    async def save_preset(self, preset: dict) -> dict:
        routes = {str(int(z)): int(s) for z, s in (preset.get("routes") or {}).items() if int(s) > 0}
        if not routes:
            raise ServiceValidationError("A preset needs at least one output")
        name = str(preset.get("name") or "Preset").strip()
        pid = preset.get("id") or next((p["id"] for p in self.presets if p["name"].casefold() == name.casefold()), None)
        clean = {"id": pid or uuid.uuid4().hex[:8], "name": name, "icon": preset.get("icon") or "mdi:television-play",
                 "routes": routes, "power_on": bool(preset.get("power_on", True)), "power_off_others": bool(preset.get("power_off_others", False))}
        for i, p in enumerate(self.presets):
            if p["id"] == clean["id"]:
                self.presets[i] = clean
                break
        else:
            self.presets.append(clean)
        await self.async_save()
        async_dispatcher_send(self.hass, SIGNAL_SETTINGS.format(self.entry_id))
        self._fire()
        return clean

    async def delete_preset(self, pid: str) -> None:
        self.settings["presets"] = [p for p in self.presets if p["id"] != pid]
        await self.async_save()
        async_dispatcher_send(self.hass, SIGNAL_SETTINGS.format(self.entry_id))
        self._fire()

    async def apply_preset(self, key: str) -> None:
        p = self.get_preset(key)
        by_input: dict[int, list[int]] = {}
        for z, s in p["routes"].items():
            by_input.setdefault(int(s) - 1, []).append(int(z) - 1)
        for inp, outs in by_input.items():
            await self.route(outs, inp, power_on=p.get("power_on", True))
        if p.get("power_off_others"):
            others = [b for b in self.outputs if str(b + 1) not in p["routes"]]
            if others:
                await self.cec_power("Output", others, False)

    # ---- panel snapshot (numbers are 1-based; 0 = nothing) ---------------------
    def snapshot(self) -> dict[str, Any]:
        hid_in, hid_out = set(self.settings["hidden_inputs"]), set(self.settings["hidden_outputs"])
        outs = []
        fed: dict[int, list[int]] = {}
        for b in sorted(self.outputs):
            src = self.source_of(b)
            if src is not None:
                fed.setdefault(src, []).append(b + 1)
            d = self.out_details.get(b) or {}
            hdbt = self.is_hdbt(b)
            lq = link_quality(first(d, "LinkQuality")) if hdbt else None
            power = self.tv_power(b)
            outs.append({
                "zone": b + 1, "name": self.output_name(b), "hidden": b + 1 in hid_out,
                "kind": "hdbt" if hdbt else "hdmi", "port_type": self.port_type(b) or None,
                "hdbt_variant": self.hdbt_variant(b) if hdbt else None,
                "cec_version": first(self.outputs[b], "CEC_version", "CECVersion"),
                "allowed_sources": [x + 1 for x in a] if (a := self.allowed_sources(b)) is not None else None,
                "source": (src + 1) if src is not None else 0,
                "audio_source": (a + 1) if (a := self.audio_source_of(b)) is not None else 0,
                "tv_power": power, "power": None if power is None else power in ("on", "turning_on"),
                "signal": as_bool(first(self.outputs[b], "HasSignal", default=first(d, "HasSignal"))),
                "hpd": as_bool(first(self.outputs[b], "HPD", default=first(d, "HPD"))),
                "monitor": first(d, "MonitorName"), "video": first(d, "Signal"), "hdcp": first(d, "HDCP"),
                "status_message": first(d, "StatusMessage", "ReportedStatus"),
                "link": None if not hdbt else {
                    "status": first(d, "LinkStatus"), "linked": as_bool(first(d, "LinkStatus")),
                    "cable_m": first(d, "EstimatedCableLength"), "poe": as_bool(first(d, "POE")),
                    "quality": lq, "transmitter": {k: v for k, v in d.items() if "firmware" in k.lower() or "transmitter" in k.lower()},
                    "receiver": self.remote.get(b) and {k: v for k, v in self.remote[b].items() if k != "Result" and not isinstance(v, (dict, list))},
                },
            })
        ins = []
        for b in sorted(self.inputs):
            d = self.in_details.get(b) or {}
            audio = self.is_audio_input(b)
            sig = as_bool(first(self.inputs[b], "HasSignal", default=first(d, "HasSignal")))
            ins.append({
                "source": b + 1, "name": self.input_name(b), "kind": "audio" if audio else "hdmi",
                "index": b + 1, "hidden": b + 1 in hid_in, "zones": fed.get(b, []),
                "signal": None if sig is None else ("signal" if sig else "no_signal"),
                "hpd": as_bool(first(self.inputs[b], "HPD")), "video": first(d, "Signal"),
                "edid": self.edid_profile(b),
            })
        h = self.health
        temps = {k[11:]: v for k, v in h.items() if k.startswith("Temperature") and k[11:].isdigit()}
        return {
            "entry_id": self.entry_id, "title": self.title, "connected": self.connected, "auth_error": self.auth_error,
            "host": self.client.host, "model": self.model_name, "model_code": self.model_code,
            "firmware": first(self.details, "Version"), "serial": self.serial,
            "mac": first(self.details, "MAC", "Mac"), "hardware_revision": first(self.details, "HardwareRevision", "BoardRev"),
            "status_message": first(h, "StatusMessage", default=first(self.details, "StatusMessage")),
            "health": {k: v for k, v in h.items() if k != "Result" and not k.startswith("Temperature") and not isinstance(v, (dict, list))},
            "temperatures": temps, "uptime": first(h, "Uptime"),
            "features": {"cec": as_bool(first(self.features, "CEC")), "cec_switching": as_bool(first(self.features, "CEC_Switching")),
                         "manual_audio": as_bool(first(first(self.features, "Audio"), "SupportManualMode"))},
            "modes": {"sink": as_bool(first(self.modes.get("sink"), "SinkMode")), "independent_audio": as_bool(first(self.modes.get("manual"), "manual_mode")),
                      "cec_on_route": as_bool(first(self.modes.get("auto_on"), "Setting"))},
            "network": {k: v for k, v in (self.modes.get("network") or {}).items() if k != "Result" and not isinstance(v, (dict, list))},
            "mirrors": [{"bay": b + 1, "name": str(first(p, "Name", default="") or f"Mirror {b + 1}"),
                         "type": first(p, "Type"),
                         "source": (s + 1) if (s := self.mirror_source_of(b)) is not None else 0,
                         "tv_power": CEC_POWER.get(as_int(first(p, "DPS")))} for b, p in sorted(self.mirrors.items())],
            "leds": {"status": first(self.features, "StatusLED"), "backlight": first(self.features, "BacklightLED")},
            "update_interval_ms": as_int(first(self.features, "UpdInterval")),
            "monitoring": {"last_contact_s": as_int(first(self.monitoring, "LastContact")),
                           "installer_id": first(self.monitoring, "InstallerId") or None},
            "system_status_code": as_int(first(self.details, "Status")),
            "psu": [{"name": first(x, "name", "Name", default=f"Supply {i + 1}"), "value": first(x, "value", "Value"),
                     "ok": as_bool(first(x, "ok", "OK"))} for i, x in enumerate(self.psu)],
            "edid_options": [{"value": k, "label": v} for k, v in self.edid_options().items()],
            "udp": {"active": self.udp_active, "last": self.last_udp, "packets": self.udp_packets},
            "zone_count": len(self.outputs), "last_update": self.last_update, "last_detail": self.last_detail,
            "server_time": time.time(), "errors": list(self.errors),
            "inputs": ins, "outputs": outs, "presets": self.presets, "groups": self.settings["groups"],
        }
