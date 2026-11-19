"""Async client for Pulse-Eight (Zektor) ProAudio DSP audio matrices.

Protocol: raw TCP socket on port 50005 (or RS-232), ASCII frames ``^CMD params$``.
Reference: "ProAudio Universal Serial Protocol" v1.1 and Pulse-Eight's open
source Control4 drivers (github.com/Pulse-Eight/drivers).

Response types:
  ``^+$``          acknowledgement (may be disabled via XS ACK bit)
  ``^!n$``         error n
  ``^=CMD ...$``   query response / parameter-changed notification. May carry a
                   breakaway suffix, e.g. ``^=SZ.2 @001,003$``.

The client keeps one persistent connection, parses every ``=`` frame into
``ProAudioState`` (so changes made from the front panel or other controllers
are picked up when the unit's ASY bit is set), and also polls periodically.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
import logging
import re
import time
from typing import Any

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 50005

ERROR_CODES: dict[int, str] = {
    1: "Unrecognised command",
    2: "Parameter out of range",
    3: "Syntax error / badly formed command",
    4: "Reserved",
    5: "Too many or too few parameters",
    6: "Device busy",
    7: "Buffer overflow",
    8: "Command not valid while the unit is powered off",
}

# XS settings1 bits
XS_ASY = 1
XS_ACK = 2
XS_ECO = 4
XS_CRE = 16
XS_XIO = 32768

AUDIO_TYPES = {0: "analog", 1: "no_signal", 2: "pcm", 3: "encoded"}


def error_message(code: int) -> str:
    if 100 <= code < 200:
        return "Error initialising the audio subsystem"
    return ERROR_CODES.get(code, "Unknown error")


class ProAudioError(Exception):
    """Base error."""


class ProAudioConnectionError(ProAudioError):
    """Not connected / connection lost / timeout."""


class ProAudioCommandError(ProAudioError):
    """The unit answered ``^!n$``."""

    def __init__(self, code: int, command: str) -> None:
        self.code = code
        self.command = command
        super().__init__(f"{command} -> error {code}: {error_message(code)}")


# --------------------------------------------------------------------------
# Model / IO layout
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelSpec:
    zones: int
    analog: int
    coax: int
    optical: int


MODELS: dict[str, ModelSpec] = {
    "ProAudio8": ModelSpec(8, 8, 8, 8),
    "ProAudio16": ModelSpec(16, 16, 16, 16),
    "ProAudio1632": ModelSpec(32, 16, 16, 8),
    "ProAudio32": ModelSpec(32, 32, 32, 16),
    "ProAudio48": ModelSpec(48, 32, 32, 16),
    "ProAudio64": ModelSpec(64, 32, 32, 16),
}
FALLBACK_MODEL = MODELS["ProAudio32"]


def model_spec(model: str | None) -> ModelSpec:
    if not model:
        return FALLBACK_MODEL
    key = model.replace(" ", "").replace("-", "")
    for name, spec in MODELS.items():
        if key.lower() == name.lower():
            return spec
    digits = re.findall(r"\d+", key)
    if digits:
        for name, spec in MODELS.items():
            if name.endswith(digits[0]):
                return spec
    return FALLBACK_MODEL


@dataclass(frozen=True)
class InputDef:
    source: int          # protocol source number
    kind: str            # analog | coax | optical
    index: int           # 1-based index within its kind

    @property
    def default_name(self) -> str:
        return f"{self.kind.capitalize()} {self.index}"


def build_inputs(spec: ModelSpec, xio: bool) -> list[InputDef]:
    """Source numbers for analog zones (SZ), per model and XIO mode."""
    inputs: list[InputDef] = []
    if xio:
        bases = {"analog": 0, "coax": 32, "optical": 64}
    else:
        bases = {"analog": 0, "coax": spec.analog, "optical": spec.analog + spec.coax}
    for kind, count in (("analog", spec.analog), ("coax", spec.coax), ("optical", spec.optical)):
        for i in range(1, count + 1):
            inputs.append(InputDef(bases[kind] + i, kind, i))
    return inputs


def zone_spec(zones: Iterable[int]) -> str:
    """Compress zones into protocol form, e.g. [1,2,3,5] -> '@1:3@5'."""
    nums = sorted(set(int(z) for z in zones))
    if not nums:
        raise ValueError("No zones given")
    parts: list[str] = []
    start = prev = nums[0]
    for n in nums[1:] + [None]:  # type: ignore[list-item]
        if n is not None and n == prev + 1:
            prev = n
            continue
        parts.append(f"@{start}" if start == prev else f"@{start}:{prev}")
        if n is not None:
            start = prev = n
    return "".join(parts)


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

@dataclass
class ZoneState:
    source: int | None = None
    power: bool | None = None
    volume: int | None = None        # VPZ 0-100
    muted: bool | None = None        # VMZ (volume mute)
    hard_muted: bool | None = None   # MZ (disconnect mute)
    audio_type: int | None = None    # ATZ


@dataclass
class ProAudioState:
    model: str | None = None
    firmware: str | None = None
    serial: str | None = None
    power: int | None = None              # 0 off, 1 on, 3 locked on
    master_volume: int | None = None      # 0-248, 200 = 0 dB
    xs1: int | None = None
    xs2: int | None = None
    ip: dict[str, str] = field(default_factory=dict)
    zones: dict[int, ZoneState] = field(default_factory=dict)
    connected: bool = False
    last_update: float | None = None
    errors: deque = field(default_factory=lambda: deque(maxlen=25))

    @property
    def spec(self) -> ModelSpec:
        return model_spec(self.model)

    @property
    def xio(self) -> bool:
        return bool(self.xs1 and self.xs1 & XS_XIO)

    @property
    def is_on(self) -> bool:
        return self.power in (1, 3)

    def zone(self, number: int) -> ZoneState:
        return self.zones.setdefault(number, ZoneState())


def master_db(raw: int | None) -> float | None:
    if raw is None:
        return None
    if raw <= 0:
        return -100.0  # full mute
    return (raw - 200) / 2


def master_raw(db: float) -> int:
    if db <= -100:
        return 0
    return max(1, min(248, round(db * 2 + 200)))


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

_FRAME_RE = re.compile(r"\^([^\^\$]*)\$")


def parse_frames(buffer: str) -> tuple[list[str], str]:
    """Extract complete ``^...$`` frames. Returns (frames, remainder)."""
    frames: list[str] = []
    last_end = 0
    for match in _FRAME_RE.finditer(buffer):
        frames.append(match.group(1).strip())
        last_end = match.end()
    remainder = buffer[last_end:]
    # Drop junk before an unfinished frame start.
    start = remainder.find("^")
    remainder = remainder[start:] if start >= 0 else ""
    return frames, remainder


def split_response(body: str) -> tuple[str, str]:
    """'=SZ.2 @001,003' -> ('SZ', '@001,003')."""
    body = body[1:] if body.startswith("=") else body
    if " " in body:
        cmd, params = body.split(" ", 1)
    else:  # parameters glued to command (spaces optional)
        m = re.match(r"([A-Za-z]+)(.*)", body)
        cmd, params = (m.group(1), m.group(2)) if m else (body, "")
    cmd = cmd.split(".", 1)[0]  # strip breakaway suffix
    return cmd, params.strip()


def parse_zone_params(params: str) -> tuple[int, list[str]] | None:
    """'@001,003' -> (1, ['003'])."""
    m = re.match(r"@\s*(\d+)\s*,?(.*)", params)
    if not m:
        return None
    rest = [p.strip() for p in m.group(2).split(",") if p.strip() != ""]
    return int(m.group(1)), rest


def apply_response(state: ProAudioState, body: str) -> str | None:
    """Update ``state`` from one '=' frame. Returns the command name."""
    cmd, params = split_response(body)
    zone_cmds = {"SZ", "PZ", "VPZ", "VMZ", "MZ", "ATZ"}
    if cmd in zone_cmds:
        parsed = parse_zone_params(params)
        if not parsed or not parsed[1]:
            return cmd
        number, values = parsed
        try:
            value = int(values[0])
        except ValueError:
            return cmd
        z = state.zone(number)
        if cmd == "SZ":
            z.source = value
        elif cmd == "PZ":
            z.power = value == 1
        elif cmd == "VPZ":
            z.volume = value
        elif cmd == "VMZ":
            z.muted = value == 1
        elif cmd == "MZ":
            z.hard_muted = value == 1
        elif cmd == "ATZ":
            z.audio_type = value
        return cmd

    if cmd == "V":
        # "ProAudio32",1.23a,59B2S12345678
        m = re.match(r'\s*"([^"]*)"\s*,\s*([^,]*)\s*,?\s*(.*)', params)
        if m:
            state.model, state.firmware, state.serial = (
                m.group(1).strip(),
                m.group(2).strip(),
                m.group(3).strip() or None,
            )
        else:
            parts = [p.strip().strip('"') for p in params.split(",")]
            state.model = parts[0] if parts else None
            state.firmware = parts[1] if len(parts) > 1 else None
            state.serial = parts[2] if len(parts) > 2 else None
    elif cmd == "P":
        try:
            state.power = int(params)
        except ValueError:
            pass
    elif cmd == "MV":
        try:
            state.master_volume = int(params)
        except ValueError:
            pass
    elif cmd == "XS":
        parts = [p.strip() for p in params.split(",")]
        try:
            state.xs1 = int(parts[0])
            if len(parts) > 1 and parts[1]:
                state.xs2 = int(parts[1])
        except ValueError:
            pass
    elif cmd in ("IPAX", "IPMX", "IPGX", "IPA", "IPM", "IPG"):
        octets = [p.strip() for p in params.split(",")]
        try:
            state.ip[cmd] = ".".join(str(int(o)) for o in octets)
        except ValueError:
            state.ip[cmd] = params
    elif cmd == "IPSET":
        state.ip["mode"] = "dhcp" if params.strip() == "1" else "static"
    return cmd


# --------------------------------------------------------------------------
# Client
# --------------------------------------------------------------------------

class ProAudioClient:
    """Persistent connection to one ProAudio unit."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        *,
        poll_interval: float = 30.0,
        command_timeout: float = 2.0,
    ) -> None:
        self.host = host
        self.port = port
        self.poll_interval = poll_interval
        self.command_timeout = command_timeout
        self.state = ProAudioState()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._buffer = ""
        self._lock = asyncio.Lock()
        self._pending: asyncio.Future[int] | None = None  # resolves with 0 or error code
        self._waiters: dict[str, list[asyncio.Future[str]]] = {}
        self._listeners: list[Callable[[], None]] = []
        self._notify_handle: asyncio.TimerHandle | None = None
        self._tasks: set[asyncio.Task] = set()
        self._stopping = False
        self._first_refresh = asyncio.Event()
        self._query_style = "?"   # '@1:32?' ; alternatives ',?' and ''

    # ---- listeners ----------------------------------------------------------
    def add_listener(self, callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def remove() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return remove

    def _schedule_notify(self) -> None:
        if self._notify_handle is not None:
            return
        loop = asyncio.get_running_loop()
        self._notify_handle = loop.call_later(0.05, self._notify)

    def _notify(self) -> None:
        self._notify_handle = None
        for cb in list(self._listeners):
            try:
                cb()
            except Exception:  # noqa: BLE001
                _LOGGER.exception("ProAudio listener failed")

    # ---- lifecycle ----------------------------------------------------------
    async def start(self, wait: float | None = 10.0) -> None:
        """Start connection + poll loops. Optionally wait for first full refresh."""
        self._stopping = False
        self._spawn(self._run())
        if wait:
            try:
                await asyncio.wait_for(self._first_refresh.wait(), wait)
            except TimeoutError as err:
                await self.stop()
                raise ProAudioConnectionError(
                    f"No response from ProAudio at {self.host}:{self.port}"
                ) from err

    async def stop(self) -> None:
        self._stopping = True
        for task in list(self._tasks):
            task.cancel()
        for task in list(self._tasks):
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        await self._close()

    def _spawn(self, coro) -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _close(self) -> None:
        writer, self._writer, self._reader = self._writer, None, None
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        if self.state.connected:
            self.state.connected = False
            self._schedule_notify()
        self._fail_pending()

    def _fail_pending(self) -> None:
        if self._pending and not self._pending.done():
            self._pending.set_exception(ProAudioConnectionError("Connection lost"))
        for futs in self._waiters.values():
            for fut in futs:
                if not fut.done():
                    fut.set_exception(ProAudioConnectionError("Connection lost"))
        self._waiters.clear()

    async def _run(self) -> None:
        backoff = 2.0
        while not self._stopping:
            try:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), 5
                )
            except (OSError, TimeoutError) as err:
                _LOGGER.debug("Connect to %s:%s failed: %s", self.host, self.port, err)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)
                continue
            backoff = 2.0
            self._buffer = ""
            self.state.connected = True
            self._schedule_notify()
            reader_task = self._spawn(self._read_loop())
            try:
                await self._initialise()
                self._first_refresh.set()
                while not reader_task.done():
                    await asyncio.wait({reader_task}, timeout=self.poll_interval)
                    if reader_task.done():
                        break
                    await self.refresh()
            except ProAudioError as err:
                _LOGGER.debug("ProAudio session error: %s", err)
            finally:
                reader_task.cancel()
                await self._close()
            if not self._stopping:
                await asyncio.sleep(backoff)

    async def _read_loop(self) -> None:
        assert self._reader is not None
        while True:
            try:
                data = await self._reader.read(4096)
            except OSError:
                data = b""
            if not data:
                _LOGGER.debug("ProAudio closed the connection")
                self.state.connected = False
                self._fail_pending()
                self._schedule_notify()
                return
            self._buffer += data.decode("ascii", errors="replace")
            frames, self._buffer = parse_frames(self._buffer)
            for frame in frames:
                self._handle_frame(frame)

    def _handle_frame(self, frame: str) -> None:
        if not frame:
            return
        kind = frame[0]
        if kind == "+":
            if self._pending and not self._pending.done():
                self._pending.set_result(0)
        elif kind == "!":
            codes = [int(c) for c in re.findall(r"\d+", frame)] or [0]
            for code in codes:
                self.state.errors.append(
                    {"time": time.time(), "code": code, "message": error_message(code),
                     "command": getattr(self, "_last_command", "")}
                )
            if self._pending and not self._pending.done():
                self._pending.set_result(codes[0])
            self._schedule_notify()
        elif kind == "=":
            cmd = apply_response(self.state, frame)
            self.state.last_update = time.time()
            if cmd:
                for fut in self._waiters.pop(cmd, []):
                    if not fut.done():
                        fut.set_result(frame)
            self._schedule_notify()
        else:
            _LOGGER.debug("Unknown frame from ProAudio: %r", frame)

    # ---- low-level send -----------------------------------------------------
    @property
    def _ack_enabled(self) -> bool | None:
        if self.state.xs1 is None:
            return None
        return bool(self.state.xs1 & XS_ACK)

    async def command(
        self, cmd: str, *, raise_on_error: bool = True, fire: bool = False
    ) -> int:
        """Send ``^cmd$``. Returns 0 on success or the error code.

        With ACK enabled we wait for ``^+$``/``^!n$``. With ACK disabled (some
        controllers turn it off) there is no positive confirmation, so we wait
        a short window for an error before assuming success.
        """
        if self._writer is None:
            raise ProAudioConnectionError("Not connected")
        if fire and self._ack_enabled is False:
            # Queries with ACK off: nothing to wait for; barrier() syncs later.
            async with self._lock:
                self._last_command = cmd
                self._writer.write(f"^{cmd}$".encode("ascii"))
                await self._writer.drain()
            return 0
        async with self._lock:
            loop = asyncio.get_running_loop()
            self._pending = loop.create_future()
            self._last_command = cmd
            self._writer.write(f"^{cmd}$".encode("ascii"))
            await self._writer.drain()
            ack = self._ack_enabled
            try:
                if ack is False:
                    try:
                        code = await asyncio.wait_for(asyncio.shield(self._pending), 0.3)
                    except TimeoutError:
                        code = 0
                else:
                    try:
                        code = await asyncio.wait_for(
                            asyncio.shield(self._pending),
                            self.command_timeout if ack else 0.6,
                        )
                    except TimeoutError as err:
                        if ack is None:
                            code = 0  # unknown ACK mode: treat silence as OK
                        else:
                            raise ProAudioConnectionError(f"Timeout waiting for reply to {cmd}") from err
            finally:
                self._pending = None
        if code and raise_on_error:
            raise ProAudioCommandError(code, cmd)
        return code

    async def barrier(self) -> None:
        """Wait until all previously sent queries have been answered.

        Responses arrive in order, so once the reply to a trailing ``V?`` is
        seen every earlier query has been answered too.
        """
        fut: asyncio.Future[str] = asyncio.get_running_loop().create_future()
        self._waiters.setdefault("V", []).append(fut)
        try:
            await self.command("V?")
            await asyncio.wait_for(fut, self.command_timeout * 2)
        except TimeoutError as err:
            raise ProAudioConnectionError("Timeout waiting for ProAudio") from err
        finally:
            waiters = self._waiters.get("V", [])
            if fut in waiters:
                waiters.remove(fut)

    # ---- queries ------------------------------------------------------------
    def _zone_query(self, cmd: str, zones: str) -> str:
        if self._query_style == ",?":
            return f"{cmd} {zones},?"
        if self._query_style == "":
            return f"{cmd} {zones}"
        return f"{cmd} {zones}?"

    async def _initialise(self) -> None:
        # Learn ACK mode, model and IO numbering first.
        await self.command("XS?", raise_on_error=False)
        await self.barrier()
        await self._detect_query_style()
        await self.refresh(full=True)

    async def _detect_query_style(self) -> None:
        for style in ("?", ",?", ""):
            self._query_style = style
            code = await self.command(self._zone_query("PZ", "@1"), raise_on_error=False)
            if code in (0, 8):
                return
        self._query_style = "?"

    async def refresh(self, full: bool = False) -> None:
        """Poll everything. Ends with a barrier so state is consistent."""
        n = self.state.spec.zones
        zones = f"@1:{n}"
        cmds = ["P?", "MV?", "XS?"]
        if full:
            cmds += ["IPAX?", "IPMX?", "IPGX?", "IPSET?"]
        for c in cmds:
            await self.command(c, raise_on_error=False, fire=True)
        if self.state.is_on or self.state.power is None:
            for zc in ("SZ", "PZ", "VPZ", "VMZ", "MZ", "ATZ"):
                await self.command(self._zone_query(zc, zones), raise_on_error=False, fire=True)
        await self.barrier()

    # ---- control ------------------------------------------------------------
    async def route(self, zones: Iterable[int], source: int) -> None:
        """Map ``source`` (0 = disconnect) to the given analog zones."""
        await self.command(f"SZ {zone_spec(zones)},{int(source)}")
        self._optimistic(zones, source=int(source))

    async def clear_all(self) -> None:
        await self.route(range(1, self.state.spec.zones + 1), 0)

    async def set_zone_power(self, zones: Iterable[int], on: bool) -> None:
        await self.command(f"PZ {zone_spec(zones)},{1 if on else 0}")
        self._optimistic(zones, power=on)

    async def set_zone_mute(self, zones: Iterable[int], mute: bool) -> None:
        await self.command(f"VMZ {zone_spec(zones)},{1 if mute else 0}")
        self._optimistic(zones, muted=mute)

    async def set_zone_volume(self, zones: Iterable[int], percent: int) -> None:
        percent = max(0, min(100, int(percent)))
        await self.command(f"VPZ {zone_spec(zones)},{percent}")
        self._optimistic(zones, volume=percent)

    async def step_zone_volume(self, zones: Iterable[int], steps: int) -> None:
        sign = "+" if steps >= 0 else "-"
        await self.command(f"VPZ {zone_spec(zones)},{sign}{abs(int(steps))}")
        await self.command(self._zone_query("VPZ", zone_spec(zones)), raise_on_error=False)

    async def set_master_volume(self, raw: int) -> None:
        raw = max(0, min(248, int(raw)))
        await self.command(f"MV {raw}")
        self.state.master_volume = raw
        self._schedule_notify()

    async def set_power(self, on: bool) -> None:
        await self.command(f"P {1 if on else 0}")
        await self.command("P?", raise_on_error=False)
        if on:
            self._spawn(self.refresh())

    async def raw(self, cmd: str) -> int:
        """Send an arbitrary command (without ^ $). Returns error code or 0."""
        cmd = cmd.strip().lstrip("^").rstrip("$")
        return await self.command(cmd, raise_on_error=False)

    def _optimistic(self, zones: Iterable[int], **values: Any) -> None:
        for z in zones:
            zs = self.state.zone(int(z))
            for key, value in values.items():
                setattr(zs, key, value)
        self._schedule_notify()

    # ---- helpers ------------------------------------------------------------
    def inputs(self) -> list[InputDef]:
        return build_inputs(self.state.spec, self.state.xio)


async def probe(host: str, port: int = DEFAULT_PORT, timeout: float = 5.0) -> ProAudioState:
    """One-shot connect and read version (for config flow)."""
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except (OSError, TimeoutError) as err:
        raise ProAudioConnectionError(str(err)) from err
    state = ProAudioState()
    try:
        writer.write(b"^V?$")
        await writer.drain()
        buffer = ""
        deadline = asyncio.get_running_loop().time() + timeout
        while state.model is None:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise ProAudioConnectionError("No version response")
            data = await asyncio.wait_for(reader.read(1024), remaining)
            if not data:
                raise ProAudioConnectionError("Connection closed")
            buffer += data.decode("ascii", errors="replace")
            frames, buffer = parse_frames(buffer)
            for frame in frames:
                if frame.startswith("="):
                    apply_response(state, frame)
    except TimeoutError as err:
        raise ProAudioConnectionError("No version response") from err
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
    return state
