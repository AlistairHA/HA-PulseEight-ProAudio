"""Optional instant updates from the matrix's UDP state broadcasts (port 8811).

MatrixOS broadcasts state changes to the local subnet. Packet layout (as documented
by chrisns/pulse-eight-matrix, observed on an FF88 with MatrixOS 3.10.5-1):

* 24-byte header: ``P8`` magic, version, opaque sender bytes, little-endian message
  type at offset 20 and payload length at offset 22.
* type 0  - identity: model, serial, firmware (16-byte NUL-padded strings at 2/18/34)
* type 2  - 61-byte port records: index, mode (0 input / 1 output), bay, two routing
  bytes (equal when routed), label, name, status text, flags (u32 at 53) and a
  hardware type code. Flags: 0x08 signal, 0x10 hot-plug, CEC power mask 0x380
  (0x180 on / turning on, 0x280 standby / turning off).
* type 21 - count-prefixed temperatures in deg C.

Anything else is ignored. Packets are only accepted from the matrix's own address,
or from a sender whose identity packet carried the matrix's serial. That is
identification, not authentication: keep the matrix on an isolated network.
"""

from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)

UDP_PORT = 8811
_PORT_REC = 61


def _text(b: bytes) -> str:
    return b.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def decode(data: bytes) -> dict[str, Any] | None:
    """Decode one datagram; None if it isn't a well-formed MatrixOS packet we understand."""
    if len(data) < 24 or data[:2] != b"P8":
        return None
    kind, size = struct.unpack_from("<HH", data, 20)
    if size != len(data) - 24:
        return None
    p = data[24:]
    out: dict[str, Any] = {"type": kind, "sender": data[:20]}
    if kind == 0 and len(p) >= 50:
        out["identity"] = {"model": _text(p[2:18]), "serial": _text(p[18:34]), "version": _text(p[34:50])}
    elif kind == 2 and p and len(p) % _PORT_REC == 0 and len(p) <= 64 * _PORT_REC:
        ports = []
        for off in range(0, len(p), _PORT_REC):
            r = p[off:off + _PORT_REC]
            flags = struct.unpack_from("<I", r, 53)[0]
            power = flags & 0x380
            ports.append({
                "mode": {0: "input", 1: "output"}.get(r[1]),
                "bay": r[2],
                "route": r[3] if r[3] == r[4] and r[3] < 32 else None,
                "name": _text(r[21:37]),
                "signal": bool(flags & 0x08),
                "hpd": bool(flags & 0x10),
                # map to the libCEC codes used by the HTTP DPS field
                "dps": 0 if power == 0x180 else 1 if power == 0x280 else None,
            })
        out["ports"] = ports
    elif kind == 21 and p and p[0] == len(p) - 1 and len(p) <= 33:
        out["temperatures"] = list(p[1:])
    else:
        return None
    return out


class _Protocol(asyncio.DatagramProtocol):
    def __init__(self, listener: UdpListener) -> None:
        self.listener = listener

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        try:
            pkt = decode(data)
        except (struct.error, IndexError, ValueError):
            pkt = None
        if pkt is not None:
            self.listener.dispatch(pkt, addr[0])


class UdpListener:
    """One shared socket per port, fanned out to every matrix hub that subscribed."""

    _instances: dict[int, UdpListener] = {}

    def __init__(self, port: int) -> None:
        self.port = port
        self.transport: asyncio.DatagramTransport | None = None
        self.subscribers: dict[int, tuple[Callable[[str, dict], bool], Callable[[dict], None]]] = {}
        self._n = 0

    @classmethod
    async def subscribe(cls, port: int, accepts: Callable[[str, dict], bool], handler: Callable[[dict], None]) -> Callable[[], None]:
        inst = cls._instances.get(port)
        if inst is None:
            inst = cls(port)
            loop = asyncio.get_running_loop()
            inst.transport, _ = await loop.create_datagram_endpoint(
                lambda: _Protocol(inst), local_addr=("0.0.0.0", port), reuse_port=True, allow_broadcast=True)
            cls._instances[port] = inst
        inst._n += 1
        key = inst._n
        inst.subscribers[key] = (accepts, handler)

        def unsubscribe() -> None:
            inst.subscribers.pop(key, None)
            if not inst.subscribers:
                if inst.transport:
                    inst.transport.close()
                cls._instances.pop(port, None)
        return unsubscribe

    def dispatch(self, pkt: dict, ip: str) -> None:
        for accepts, handler in list(self.subscribers.values()):
            if accepts(ip, pkt):
                try:
                    handler(pkt)
                except Exception:  # noqa: BLE001
                    _LOGGER.exception("neo UDP update failed")


def encode_port(mode: str, bay: int, *, index: int, route: int | None = None, name: str = "",
                signal: bool = False, hpd: bool = False, dps: int | None = None) -> bytes:
    """Build one type-2 record (used by tests and the simulator)."""
    flags = (0x08 if signal else 0) | (0x10 if hpd else 0) | {0: 0x180, 1: 0x280}.get(dps, 0)
    r = bytearray(_PORT_REC)
    r[0], r[1], r[2] = index, 0 if mode == "input" else 1, bay
    r[3] = r[4] = 0xFF if route is None else route
    r[21:37] = name.encode()[:15].ljust(16, b"\0")
    struct.pack_into("<I", r, 53, flags)
    return bytes(r)


def encode(kind: int, payload: bytes, sender: bytes = b"P8\x01\x00" + bytes(16)) -> bytes:
    return sender[:20].ljust(20, b"\0") + struct.pack("<HH", kind, len(payload)) + payload
