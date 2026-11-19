"""Simulated Pulse-Eight neo:X+ (FF88SA) HTTP API for tests and UI work.

    python tests/fake_neo.py --port 8080 [--password admin]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random

from aiohttp import web

IN_NAMES = ["Sky Q", "Apple TV", "PlayStation 5", "Blu-ray", "Xbox", "Fire TV", "CCTV NVR", "Chromecast",
            "Optical 1", "Optical 2", "Coax 1", "Coax 2"]
OUT_NAMES = ["Lounge TV", "Kitchen TV", "Master Bedroom", "Gym", "Snug", "Kids Room", "Garage", "Garden Room",
             "Cinema AVR", "Bar TV"]


class FakeNeo:
    def __init__(self, password: str = "", model: str = "FF88SA", *, receive_from: bool = False) -> None:
        # receive_from=False mimics the documented Port/List (routing only via Port/List/Concise)
        self.receive_from = receive_from
        self.status_led = "on"
        self.backlight = "on"
        self.cec_switching = True
        self.autopause = False
        self.combokeys = True
        self.edid = [11] * 8
        self.ir = [1] * 10
        self.allowed = {7: [0, 1, 5, 7]}  # Garden Room: Sky Q, Apple TV, Fire TV, Chromecast only
        self.password = password
        self.model = model
        self.inputs = [{"name": n, "signal": i not in (6, 9, 11), "hpd": i not in (6,)} for i, n in enumerate(IN_NAMES)]
        routes = [0, 1, 0, 3, 2, 7, 6, 1, 0, 2]
        self.outputs = [{
            "name": n, "src": routes[i], "audio": routes[i],
            "dps": [0, 0, 1, 1, 0, 1, -1, 1, 0, 1][i],
            "hpd": i != 6, "link": i not in (6,),
            "mse": None if i == 6 else ([-21.0, -22.4, -20.8, -21.9] if i != 3 else [-14.2, -19.5, -16.1, -21.0]),
            "cable": [22, 18, 31, 64, 12, 27, None, 45, None, None][i],
        } for i, n in enumerate(OUT_NAMES)]
        self.cec_enabled = True
        self.calls: list[tuple[str, str, object]] = []
        self.online = True
        self.runner: web.AppRunner | None = None

    # ------------------------------------------------------------------
    def _port_in(self, i: int) -> dict:
        p = self.inputs[i]
        d = {"Bay": i, "Mode": "Input", "Type": "HDMI2" if i < 8 else "audio", "Status": 0, "Name": p["name"],
             "DPS": -1, "HasSignal": p["signal"], "HPD": p["hpd"]}
        if self.receive_from:
            d["ReceiveFrom"] = -1
        return d

    def _port_out(self, i: int) -> dict:
        p = self.outputs[i]
        d = {"Bay": i, "Mode": "Output", "Type": ("HDBT-TXPRO" if i < 6 else "HDBT-TXLITE") if i < 8 else "HDMI2",
             "Status": 0, "Name": p["name"], "AudioRecieved": p["audio"], "DPS": p["dps"], "CEC_version": 4,
             "HasSignal": self.inputs[p["src"]]["signal"] and p["hpd"], "HPD": p["hpd"]}
        if self.receive_from:
            d["ReceiveFrom"] = p["src"]
        return d

    def _port_mirror(self) -> dict:
        # neo:X+ style local HDMI mirror of output 1
        d = {"Bay": 0, "Mode": "Mirror", "Type": "HDMI", "Status": 0, "Name": "Rack monitor", "DPS": -2}
        if self.receive_from:
            d["ReceiveFrom"] = self.outputs[0]["src"]
        return d

    def _details_out(self, i: int) -> dict:
        p = self.outputs[i]
        d = {"Result": True, **self._port_out(i), **({"AllowedSources": self.allowed[i]} if i in self.allowed else {}), "MonitorName": ["SAMSUNG", "LG TV", "SONY TV", "Hisense"][i % 4] if p["hpd"] else "",
             "Signal": "3840x2160p60 YCbCr 4:2:0 8-bit" if p["hpd"] else "No signal", "HDCP": 2 if p["hpd"] else 0,
             "StatusMessage": "OK" if p["link"] or i >= 8 else "No HDBaseT link"}
        if i < 8:
            d["LinkStatus"] = "Linked" if p["link"] else "No Link"
            d["POE"] = p["link"]
            d["TransmitterFirmware"] = "2.4.4.0"
            if p["link"]:
                a, b, c, dd = (v + random.uniform(-0.3, 0.3) for v in p["mse"])
                d["EstimatedCableLength"] = p["cable"]
                d["LinkQuality"] = {"ChannelA": round(a, 1), "ChannelB": round(b, 1), "ChannelC": round(c, 1), "ChannelD": round(dd, 1),
                                    "BER": 0, "TotalBER": 0 if i != 3 else 12, "ErrorsCRC": 0 if i != 3 else 3, "ErrorsVideo": 0}
        return d

    # ------------------------------------------------------------------
    async def handler(self, request: web.Request) -> web.Response:
        path = request.path.strip("/")
        low = path.lower()
        body = None
        if request.can_read_body:
            try:
                body = json.loads(await request.text() or "null")
            except ValueError:
                body = None
        self.calls.append((request.method, path, body))
        if not self.online:
            raise web.HTTPServiceUnavailable()
        if low == "account/login":
            if body and body.get("Password") == self.password:
                resp = web.json_response({"Result": True})
                resp.set_cookie("neo_session", "ok")
                return resp
            return web.json_response({"Result": False, "ErrorMessage": "Invalid password"})
        if self.password and request.cookies.get("neo_session") != "ok":
            return web.Response(status=403)
        j = lambda d: web.json_response({"Result": True, **d})  # noqa: E731
        if low == "system/details":
            return j({"Model": self.model, "Serial": "P8SN0123456", "Version": "4.12.3", "StatusMessage": "System Healthy",
                      "MAC": "00:1E:C0:12:34:56", "VID": "P8", "BoardRev": 3, "Status": 0})
        if low == "system/health":
            return j({"Temperature0": 41, "Temperature1": 38, "Temperature2": 45, "Temperature3": 36, "Temperature4": 39,
                      "Uptime": 352800, "StatusMessage": "System Healthy", "PSU1": 0, "PSU1Message": "OK",
                      "InputModulesMessage": "OK", "OutputModulesMessage": "OK",
                      "psu": [{"name": "12V", "value": 12.08, "ok": True}, {"name": "5V", "value": 5.02, "ok": True},
                              {"name": "3.3V", "value": 3.31, "ok": True}]})
        if low == "system/features":
            return j({"CEC": self.cec_enabled, "CEC_Switching": True, "UpdInterval": 3600000, "CEC_Logging": 0, "CEC_Usage": 8,
                      "BacklightLED": self.backlight, "StatusLED": self.status_led,
                      "Video": {"Input": {"Bays": 8}, "Output": {"Bays": 10}, "Scrambling": True},
                      "Audio": {"Routing": True, "SupportManualMode": True, "Input": {"Bays": 4}, "Output": {"Bays": 10}}})
        if low == "audio/sinkmode":
            return j({"SinkMode": True})
        if low == "audio/manualmode":
            return j({"manual_mode": False})
        if low == "cec/autopoweron":
            return j({"Setting": True})
        if low == "network/settings":
            return j({"DHCP": True, "IPAddress": "192.168.1.70", "Subnet": "255.255.255.0", "Gateway": "192.168.1.1"})
        if low == "port/list":
            return j({"Ports": [self._port_in(i) for i in range(12)] + [self._port_out(i) for i in range(10)] + [self._port_mirror()]})
        if low == "port/list/concise":
            return j({**{f"Output{i + 1}": [o["src"]] for i, o in enumerate(self.outputs)}, "Mirror1": [self.outputs[0]["src"]]})
        if low == "monitoring/settings":
            return j({"LastContact": 600, "InstallerId": "1234"})
        parts = low.split("/")
        if parts[:2] == ["port", "details"] and len(parts) == 4:
            mode, bay = parts[2], int(parts[3])
            if mode == "output" and 0 <= bay < 10:
                return web.json_response(self._details_out(bay))
            if mode == "input" and 0 <= bay < 12:
                return j({**self._port_in(bay), "Signal": "3840x2160p60" if self.inputs[bay]["signal"] else "No signal",
                      **({"EdidProfile": self.edid[bay]} if bay < 8 else {})})
            return web.json_response({"Result": False, "ErrorMessage": "Invalid port"})
        if parts[:2] == ["port", "remotedetails"] and len(parts) == 4:
            bay = int(parts[3])
            if parts[2] == "output" and bay < 8 and self.outputs[bay]["link"]:
                return j({"Model": "neo:Ultra Receiver", "Firmware": "1.9.2", "Serial": f"P8RX00{bay}42", "Temperature": 48 + bay})
            return web.json_response({"Result": False, "ErrorMessage": "No remote module"})
        if parts[:2] == ["port", "set"] and len(parts) == 4:
            i, o = int(parts[2]), int(parts[3])
            if not (0 <= i < 8 and 0 <= o < 10) or (o in self.allowed and i not in self.allowed[o]):
                return web.json_response({"Result": False, "ErrorMessage": "Invalid port"})
            self.outputs[o]["src"] = i
            self.outputs[o]["audio"] = i
            return j({"Message": "Changed"})
        if parts[:2] == ["audio", "route"] and len(parts) == 4:
            i, o = int(parts[2]), int(parts[3])
            self.outputs[o]["audio"] = i
            return j({"Message": "Changed"})
        if parts[0] == "cec" and len(parts) == 4 and parts[1] in ("on", "off"):
            bay = int(parts[3])
            if parts[2] == "output":
                self.outputs[bay]["dps"] = 0 if parts[1] == "on" else 1
            return j({"Message": "Sent"})
        if parts[:2] == ["cec", "volume"] and len(parts) == 5:
            if parts[2] not in ("up", "down", "mute"):
                return web.json_response({"Result": False, "ErrorMessage": "Invalid method"})
            return j({})
        if low == "cec/autopause":
            if request.method == "POST":
                self.autopause = bool(body["AutoPause"])
            return j({"AutoPause": self.autopause})
        if low == "cec/combokeys":
            return j({"ComboKeys": self.combokeys})
        if parts[:3] == ["cec", "combokeys", "set"] and len(parts) == 4:
            self.combokeys = parts[3] == "true"
            return j({})
        if low in ("cec/enable", "cec/disable") and request.method == "POST":
            self.cec_enabled = low == "cec/enable"
            return j({})
        if parts[:2] == ["cec", "switching"] and len(parts) == 3 and request.method == "POST":
            self.cec_switching = parts[2] == "on"
            return j({})
        if parts[:2] == ["system", "backlightled"] and len(parts) == 3 and request.method == "POST":
            self.backlight = parts[2]
            return j({"Message": "Changed"})
        if low == "ir/profiles":
            return j({"Profiles": [{"Id": 1, "Name": "Pulse-Eight remote"}, {"Id": 2, "Name": "Sky Q"}, {"Id": 3, "Name": "Apple TV"}]})
        if parts[:2] == ["ir", "details"] and len(parts) == 3:
            return j({"Id": self.ir[int(parts[2])]})
        if parts[:2] == ["ir", "setprofile"] and len(parts) == 3 and request.method == "POST":
            self.ir[int(parts[2])] = int(body["Profile"])
            return j({})
        if parts[:3] == ["port", "edid", "set"] and len(parts) == 5:
            prof, bay = int(parts[3]), int(parts[4])
            if not 0 <= bay < 8:
                return web.json_response({"Result": False, "ErrorMessage": "Invalid port"})
            self.edid[bay] = prof
            return j({})
        if parts[:2] == ["system", "statusled"] and len(parts) == 3 and request.method == "POST":
            self.status_led = parts[2]
            return j({"Message": "Changed"})
        if parts[:2] == ["cec", "key"]:
            return j({"Message": "Transmitted"})
        if parts[:2] == ["port", "setname"] and len(parts) == 4:
            bay = int(parts[3])
            (self.outputs if parts[2] == "output" else self.inputs)[bay]["name"] = body["Name"]
            return j({"Message": "Name changed"})
        if low == "system/restart":
            return j({})
        return web.json_response({"Result": False, "ErrorMessage": "Unknown command"}, status=404)

    def udp_state(self) -> list[bytes]:
        """Identity + port-state datagrams, as the matrix broadcasts them."""
        from custom_components.pulse_eight_neo.udp import encode, encode_port  # noqa: PLC0415
        ident = bytearray(54)
        ident[2:18] = self.model.encode().ljust(16, b"\0")
        ident[18:34] = b"P8SN0123456".ljust(16, b"\0")
        ident[34:50] = b"4.12.3".ljust(16, b"\0")
        recs = [encode_port("input", i, index=i, name=p["name"], signal=p["signal"], hpd=p["hpd"]) for i, p in enumerate(self.inputs)]
        recs += [encode_port("output", i, index=12 + i, route=p["src"], name=p["name"], hpd=p["hpd"],
                             signal=self.inputs[p["src"]]["signal"] and p["hpd"], dps=p["dps"] if p["dps"] in (0, 1) else None)
                 for i, p in enumerate(self.outputs)]
        return [encode(0, bytes(ident)), encode(2, b"".join(recs)), encode(21, bytes([5, 40, 37, 44, 35, 38]))]

    def send_udp(self, port: int = 8811, host: str = "127.0.0.1") -> None:
        import socket  # noqa: PLC0415
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            for pkt in self.udp_state():
                sock.sendto(pkt, (host, port))

    async def start(self, host: str = "127.0.0.1", port: int = 0) -> int:
        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", self.handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, host, port)
        await site.start()
        return site._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()


async def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--password", default="")
    ap.add_argument("--udp", type=int, default=0, help="also send UDP state pushes to this port on 127.0.0.1")
    a = ap.parse_args()
    fake = FakeNeo(a.password)
    port = await fake.start("0.0.0.0", a.port)
    print(f"Fake neo:X+ on :{port}")
    while True:
        await asyncio.sleep(2)
        if a.udp:
            fake.send_udp(a.udp)


if __name__ == "__main__":
    asyncio.run(_main())
