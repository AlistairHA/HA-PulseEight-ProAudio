"""Async HTTP client for Pulse-Eight neo video matrices (neo:X, neo:X+, neo:8 ...).

Endpoints come from Pulse-Eight's open-source control drivers
(github.com/Pulse-Eight/drivers: Control4 neo_Common, Crestron Home, Elan, RTI)
and the protocol notes of chrisns/pulse-eight-matrix (MIT). Bays are zero-based
on the wire; this client keeps them zero-based and the integration shows
one-based numbers to people.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

MODELS = {
    "FF88SA": "neo:X+",
    "FF88S": "neo:X",
    "FF66SA": "neo:XMR",
    "FF64S": "neo:XSR",
    "FF88": "neo:8",
    "FF88A": "neo:8a",
    "FF66A": "neo:6a",
    "FFMS44": "neo:4 Professional",
    "FFMB44": "neo:4 Basic",
    "MM88": "neo:8 Modular",
}
SINK_MODE_MODELS = {"FF88SA", "FF88S", "FF66SA", "FF64S"}

# libCEC power status, as reported in the DPS field (negative values = unknown / no CEC)
CEC_POWER = {0: "on", 1: "standby", 2: "turning_on", 3: "turning_off"}

# Input EDID profiles (Port/EDID/Set/{profile}/{bay}); 101+N clones output N's display EDID.
EDID_PROFILES = {
    11: "Dynamic", 0: "1080p stereo", 4: "720p stereo", 3: "1080p Dolby 5.1", 5: "1080p 7.1",
    2: "Ultra HD 4K", 6: "Ultra HD 4K 7.1", 7: "HDR10 Dolby 5.1", 8: "HDR10 7.1",
}
EDID_HDR = {7, 8}  # only offered when System/Features reports Video.Scrambling
EDID_CLONE_BASE = 101

BACKLIGHT_OPTIONS = ("off", "on", "auto")

# CEC/Volume methods (API docs: Up, Down, Mute — Mute is a toggle)
CEC_VOLUME = ("Up", "Down", "Mute")

# CEC user-control codes (HDMI-CEC 1.4 table 27), as used by Pulse-Eight's TV driver
CEC_KEYS = {
    "select": 0x00, "up": 0x01, "down": 0x02, "left": 0x03, "right": 0x04,
    "root_menu": 0x09, "setup_menu": 0x0A, "contents_menu": 0x0B, "exit": 0x0D,
    "0": 0x20, "1": 0x21, "2": 0x22, "3": 0x23, "4": 0x24, "5": 0x25, "6": 0x26,
    "7": 0x27, "8": 0x28, "9": 0x29, "channel_up": 0x30, "channel_down": 0x31,
    "input_select": 0x34, "display_info": 0x35, "help": 0x36, "page_up": 0x37,
    "page_down": 0x38, "power": 0x40, "volume_up": 0x41, "volume_down": 0x42,
    "mute": 0x43, "play": 0x44, "stop": 0x45, "pause": 0x46, "record": 0x47,
    "rewind": 0x48, "fast_forward": 0x49, "eject": 0x4A, "forward": 0x4B,
    "backward": 0x4C, "epg": 0x53, "power_toggle": 0x6B, "power_off": 0x6C,
    "power_on": 0x6D, "blue": 0x71, "red": 0x72, "green": 0x73, "yellow": 0x74,
    # additional codes from the Pulse-Eight API docs (CEC/Key table)
    "back": 0x0D, "favorite_menu": 0x0C, "media_top_menu": 0x10, "media_context_menu": 0x11,
    "dot": 0x2A, "enter": 0x2B, "clear": 0x2C, "previous_channel": 0x32, "sound_select": 0x33,
    "record_stop": 0x4D, "angle": 0x50, "subtitle": 0x51, "video_on_demand": 0x52,
    "audio_description": 0x58, "internet": 0x59, "3d_mode": 0x5A, "select_av_input": 0x69,
    "select_audio_input": 0x6A, "f5": 0x75, "data": 0x76,
}


class NeoError(Exception):
    """Base error."""


class NeoConnectionError(NeoError):
    """Unreachable / bad response."""


class NeoNotFound(NeoConnectionError):
    """HTTP 404: this firmware doesn't have the endpoint."""


class NeoAuthError(NeoError):
    """Login required or password rejected."""


class NeoApiError(NeoError):
    """Matrix answered Result=false."""


def first(data: dict | None, *keys: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    for k in keys:
        if data.get(k) is not None:
            return data[k]
    low = {k.lower(): v for k, v in data.items()}
    for k in keys:
        if low.get(k.lower()) is not None:
            return low[k.lower()]
    return default


def as_int(v: Any) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def as_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    if s in ("", "unknown", "n/a", "na", "-", "?"):
        return None
    if s in ("true", "yes", "on", "1", "linked", "connected", "active"):
        return True
    if s in ("false", "no", "off", "0", "none", "unlinked", "disconnected", "inactive", "down", "lost"):
        return False
    if s.startswith(("no ", "no_", "not ", "un", "dis")) or s.endswith(("lost", "down", "failed")):
        return False  # "No Link", "Not linked", "Unlinked", "Link lost" ...
    if "link" in s or "connect" in s or s in ("up", "ok", "good"):
        return True
    return None


def link_quality(lq: dict | None) -> dict | None:
    """Rate an HDBaseT link from its Mean Square Error channels.

    Per the neo:X+ manual: all four channels should be below -15 dB and within
    3 dB of each other, otherwise the cable is marked "Poor".
    """
    if not isinstance(lq, dict):
        return None
    chans = {}
    for c in ("A", "B", "C", "D"):
        v = first(lq, f"Channel{c}", f"MSE{c}", f"Channel_{c}")
        try:
            chans[c] = float(v)
        except (TypeError, ValueError):
            pass
    result: dict[str, Any] = {"channels": chans, "raw": {k: v for k, v in lq.items() if not isinstance(v, (dict, list))}}
    reported = first(lq, "Quality", "Status", "Rating", "LinkQuality")
    if isinstance(reported, str) and reported.strip():
        result["rating"] = reported.strip().lower()
    elif len(chans) == 4:
        vals = list(chans.values())
        good = all(v < -15 for v in vals) and (max(vals) - min(vals)) <= 3
        result["rating"] = "good" if good else "poor"
        result["worst_db"] = max(vals)
    return result


class NeoClient:
    """Serialised HTTP access to one matrix (the embedded web server is small)."""

    def __init__(self, host: str, password: str = "", *, port: int = 80, timeout: float = 15) -> None:
        host = host.strip().removeprefix("http://").rstrip("/")
        self.host = host
        self.port = port
        self.password = password
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        self._last = 0.0
        self._authed = False

    @property
    def base_url(self) -> str:
        return f"http://{self.host}" + ("" if self.port == 80 else f":{self.port}")

    def _sess(self) -> aiohttp.ClientSession:
        # Own session + unsafe cookie jar: the matrix sets its login cookie on a
        # bare IP address, which aiohttp's default jar refuses.
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _raw(self, method: str, path: str, payload: Any = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs: dict[str, Any] = {"timeout": self._timeout, "allow_redirects": False}
        if payload is not None:
            kwargs["data"] = json.dumps(payload)
            kwargs["headers"] = {"Content-Type": "application/json"}
        try:
            async with self._sess().request(method, url, **kwargs) as resp:
                text = await resp.text()
                if resp.status in (401, 403) or (resp.status in (301, 302) and "login" in resp.headers.get("Location", "").lower()):
                    self._authed = False
                    raise NeoAuthError("Matrix requires the admin password")
                if resp.status == 404:
                    raise NeoNotFound(f"{method} {path}: not supported")
                if resp.status != 200:
                    raise NeoConnectionError(f"{method} {path}: HTTP {resp.status}")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise NeoConnectionError(f"{method} {path}: {err}") from err
        try:
            data = json.loads(text, strict=False)
        except ValueError as err:
            raise NeoConnectionError(f"{path} returned non-JSON") from err
        if not isinstance(data, dict):
            raise NeoConnectionError(f"{path} returned unexpected JSON")
        return data

    async def _login(self) -> None:
        data = await self._raw("POST", "Account/Login", {"Password": self.password})
        if data.get("Result") is False:
            raise NeoAuthError("Matrix rejected the admin password")
        self._authed = True

    async def request(self, path: str, *, method: str = "GET", payload: Any = None, check: bool = True) -> dict:
        async with self._lock:
            gap = 0.08 - (time.monotonic() - self._last)
            if gap > 0:
                await asyncio.sleep(gap)
            try:
                if self.password and not self._authed:
                    await self._login()
                try:
                    data = await self._raw(method, path, payload)
                except NeoAuthError:
                    if not self.password:
                        raise
                    await self._login()  # session expired: log in again once
                    data = await self._raw(method, path, payload)
            finally:
                self._last = time.monotonic()
        _LOGGER.debug("%s %s -> %s", method, path, str(data)[:300])
        if check and data.get("Result") is False:
            raise NeoApiError(first(data, "ErrorMessage", "Message", default=f"{path} rejected"))
        return data

    # ---- reads -------------------------------------------------------------
    async def details(self) -> dict:
        return await self.request("System/Details")

    async def features(self) -> dict:
        return await self.request("System/Features")

    async def health(self) -> dict:
        return await self.request("System/Health")

    async def ports(self) -> list[dict]:
        data = await self.request("Port/List")
        ports = first(data, "Ports", default=[])
        return [p for p in ports if isinstance(p, dict)]

    async def concise_routes(self) -> dict[str, int]:
        """Port/List/Concise → {"Output1": 0, "Mirror1": 0, …} (input index per output, -1 = none)."""
        data = await self.request("Port/List/Concise")
        out: dict[str, int] = {}
        for k, v in data.items():
            if k in ("Result", "ErrorMessage"):
                continue
            if isinstance(v, list):
                v = v[0] if v else None
            iv = as_int(v)
            if iv is not None:
                out[k] = iv
        return out

    async def monitoring(self) -> dict | None:
        return await self.setting("Monitoring/Settings")

    async def port_details(self, mode: str, bay: int) -> dict:
        return await self.request(f"Port/Details/{mode}/{bay}")

    async def remote_details(self, mode: str, bay: int) -> dict:
        return await self.request(f"Port/RemoteDetails/{mode}/{bay}")

    async def setting(self, path: str) -> dict | None:
        try:
            return await self.request(path, check=False)
        except NeoConnectionError:
            return None

    # ---- control ---------------------------------------------------------------
    async def route(self, input_bay: int, output_bay: int) -> dict:
        return await self.request(f"Port/Set/{int(input_bay)}/{int(output_bay)}")

    async def audio_route(self, input_bay: int, output_bay: int) -> dict:
        return await self.request(f"Audio/Route/{int(input_bay)}/{int(output_bay)}")

    async def cec_power(self, mode: str, bay: int, on: bool) -> dict:
        return await self.request(f"CEC/{'on' if on else 'off'}/{mode}/{int(bay)}")

    async def cec_volume(self, method: str, mode: str, bay: int) -> dict:
        if method not in CEC_VOLUME:
            raise ValueError(f"volume method must be one of {CEC_VOLUME}")
        return await self.request(f"CEC/Volume/{method}/{mode}/{int(bay)}")

    async def set_status_led(self, on: bool) -> dict:
        # capitalised, as used against real hardware (chrisns/pulse-eight-matrix, FF88 MatrixOS 3.10)
        return await self.request(f"System/StatusLED/{'On' if on else 'Off'}", method="POST", payload={})

    async def set_backlight(self, value: str) -> dict:
        return await self.request(f"System/BacklightLED/{value}", method="POST", payload={})

    async def set_edid(self, profile: int, bay: int) -> dict:
        return await self.request(f"Port/EDID/Set/{int(profile)}/{int(bay)}")

    async def set_cec_enabled(self, on: bool) -> dict:
        return await self.request(f"CEC/{'Enable' if on else 'Disable'}", method="POST", payload={})

    async def set_cec_switching(self, on: bool) -> dict:
        return await self.request(f"cec/switching/{'on' if on else 'off'}", method="POST", payload={})

    async def set_cec_autopause(self, on: bool) -> dict:
        return await self.request("CEC/AutoPause", method="POST", payload={"AutoPause": bool(on)})

    async def set_cec_combokeys(self, on: bool) -> dict:
        return await self.request(f"CEC/ComboKeys/set/{'true' if on else 'false'}")

    async def set_ir_profile(self, bay: int, profile: int) -> dict:
        return await self.request(f"IR/SetProfile/{int(bay)}", method="POST", payload={"Profile": int(profile)})

    async def cec_key(self, mode: str, bay: int, code: int) -> dict:
        return await self.request(f"cec/key/{mode}/{int(bay)}", method="POST", payload={"Code": f"0x{int(code):02X}"})

    async def set_name(self, mode: str, bay: int, name: str) -> dict:
        return await self.request(f"Port/SetName/{mode}/{int(bay)}", method="POST", payload={"Name": name})

    async def restart(self) -> None:
        try:
            await self.request("System/Restart", check=False)
        except NeoConnectionError:
            pass  # it may drop the connection while rebooting
