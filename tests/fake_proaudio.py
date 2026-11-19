"""A protocol-faithful fake ProAudio unit (TCP, port 50005 style).

Usable from tests, or standalone as a simulator for UI development:

    python tests/fake_proaudio.py --port 50005 --model ProAudio32
"""

from __future__ import annotations

import argparse
import asyncio
import re

ZONE_CMDS = {"SZ", "PZ", "VPZ", "VMZ", "MZ", "ATZ"}


class FakeProAudio:
    def __init__(self, model: str = "ProAudio32", zones: int = 32, ack: bool = True,
                 breakaway: bool = False) -> None:
        self.model = model
        self.zones = zones
        self.power = 1
        self.master = 200
        self.xs1 = 1 | 4 | 16 | (2 if ack else 0)  # ASY ECO CRE (+ACK)
        self.xs2 = 6
        self.breakaway = breakaway
        self.state = {
            z: {"SZ": z if z <= 6 else 0, "PZ": 1 if z <= 8 else 0, "VPZ": 40, "VMZ": 0,
                "MZ": 0, "ATZ": 0}
            for z in range(1, zones + 1)
        }
        self.state[3]["SZ"] = 33  # coax 1
        self.state[3]["ATZ"] = 2
        self.state[4]["SZ"] = 65  # optical 1
        self.state[4]["ATZ"] = 3
        self.clients: set[asyncio.StreamWriter] = set()
        self.received: list[str] = []
        self.server: asyncio.base_events.Server | None = None

    # ------------------------------------------------------------------
    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        self.server = await asyncio.start_server(self._handle, host, port)
        return self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        for w in list(self.clients):
            w.close()
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def drop_clients(self) -> None:
        for w in list(self.clients):
            w.close()
        self.clients.clear()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.clients.add(writer)
        buf = ""
        try:
            while data := await reader.read(1024):
                buf += data.decode()
                while "$" in buf:
                    frame, buf = buf.split("$", 1)
                    if "^" not in frame:
                        continue
                    cmd = frame[frame.rfind("^") + 1:].strip()
                    self.received.append(cmd)
                    out = self.execute(cmd)
                    for line, broadcast in out:
                        targets = self.clients if broadcast else {writer}
                        for t in list(targets):
                            if t.is_closing():
                                self.clients.discard(t)
                                continue
                            t.write(f"^{line}$\r\n".encode())
                    await writer.drain()
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            self.clients.discard(writer)
            writer.close()

    # ------------------------------------------------------------------
    @property
    def ack(self) -> bool:
        return bool(self.xs1 & 2)

    def _ok(self) -> list[tuple[str, bool]]:
        return [("+", False)] if self.ack else []

    def _err(self, code: int) -> list[tuple[str, bool]]:
        return [(f"!{code}", False)]

    def _bk(self, cmd: str) -> str:
        return f"{cmd}.2" if self.breakaway and cmd == "SZ" else cmd

    def execute(self, raw: str) -> list[tuple[str, bool]]:
        raw = raw.replace(" ", "")
        m = re.match(r"([A-Za-z]+)(.*)", raw)
        if not m:
            return self._err(3)
        cmd, params = m.group(1), m.group(2)

        if cmd == "V":
            if params not in ("?", ""):
                return self._err(5)
            return self._ok() + [(f'=V "{self.model}",1.23a,59B2S12345678', False)]
        if cmd == "P":
            if params == "?":
                return self._ok() + [(f"=P {self.power}", False)]
            if params not in ("0", "1", "2", "3"):
                return self._err(2)
            v = int(params)
            self.power = {0: 0, 1: 1, 2: 0, 3: 3}[v]
            return self._ok() + [(f"=P {self.power}", True)]
        if cmd == "MV":
            if params == "?":
                return self._ok() + [(f"=MV {self.master:03d}", False)]
            try:
                v = int(params)
            except ValueError:
                return self._err(3)
            if not 0 <= v <= 248:
                return self._err(2)
            self.master = v
            return self._ok() + [(f"=MV {v:03d}", True)]
        if cmd == "XS":
            if params == "?":
                return self._ok() + [(f"=XS {self.xs1},{self.xs2}", False)]
            return self._ok()
        if cmd in ("IPAX", "IPMX", "IPGX", "IPSET"):
            val = {"IPAX": "192,168,001,060", "IPMX": "255,255,255,000",
                   "IPGX": "192,168,001,001", "IPSET": "1"}[cmd]
            return self._ok() + [(f"={cmd} {val}", False)]
        if cmd in ZONE_CMDS:
            return self._zone(cmd, params)
        return self._err(1)

    def _zone(self, cmd: str, params: str) -> list[tuple[str, bool]]:
        query = params.endswith("?")
        body = params.rstrip("?").rstrip(",")
        zones: list[int] = []
        value: str | None = None
        for token in re.findall(r"@\d+(?::\d+)?|[^,@]+", body):
            if token.startswith("@"):
                a, _, b = token[1:].partition(":")
                zones.extend(range(int(a), int(b or a) + 1))
            else:
                value = token
        if not zones:
            return self._err(3)
        if any(z < 1 or z > self.zones for z in zones):
            return self._err(2)
        if self.power == 0:
            return self._err(8)
        if query or value is None:
            return self._ok() + [
                (f"={self._bk(cmd)} @{z:03d},{self.state[z][cmd]:03d}", False) for z in zones
            ]
        if cmd == "ATZ":
            return self._err(1)
        try:
            v = int(value)
        except ValueError:
            return self._err(3)
        limits = {"SZ": 80, "PZ": 1, "VPZ": 100, "VMZ": 2, "MZ": 1}
        if not 0 <= v <= limits[cmd]:
            return self._err(2)
        if cmd == "VMZ" and v == 2:
            v = 0
        out = self._ok()
        for z in zones:
            self.state[z][cmd] = v
            out.append((f"={self._bk(cmd)} @{z:03d},{v:03d}", True))
            if cmd == "SZ":
                self.state[z]["ATZ"] = 2 if 33 <= v <= 64 else 0
        return out


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=50005)
    parser.add_argument("--model", default="ProAudio32")
    parser.add_argument("--zones", type=int, default=32)
    args = parser.parse_args()
    fake = FakeProAudio(args.model, args.zones)
    port = await fake.start("0.0.0.0", args.port)
    print(f"Fake {args.model} listening on :{port}")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(_main())
