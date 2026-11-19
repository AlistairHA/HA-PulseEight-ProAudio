"""Hub: one ProAudio unit = client + user settings (names, presets)."""

from __future__ import annotations

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
    AUDIO_TYPES,
    InputDef,
    ProAudioClient,
    ProAudioError,
    master_db,
)
from .const import DOMAIN, SIGNAL_PRESETS_UPDATED

_LOGGER = logging.getLogger(__name__)
STORE_VERSION = 1


def _default_settings() -> dict[str, Any]:
    return {"inputs": {}, "outputs": {}, "hidden_inputs": [], "hidden_outputs": [], "presets": [], "groups": []}


class ProAudioHub:
    """Owns the connection and the user-editable configuration of one unit."""

    def __init__(self, hass: HomeAssistant, entry_id: str, title: str, client: ProAudioClient) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.title = title
        self.client = client
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}")
        self.settings: dict[str, Any] = _default_settings()
        self._listeners: list[Callable[[], None]] = []
        self._unsub_client = client.add_listener(self._client_changed)

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if data:
            self.settings = {**_default_settings(), **data}

    async def async_save(self) -> None:
        await self._store.async_save(self.settings)

    async def async_remove_store(self) -> None:
        await self._store.async_remove()

    def close(self) -> None:
        self._unsub_client()

    # ---- change listeners (panel subscriptions) -----------------------------
    def add_listener(self, cb: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb) if cb in self._listeners else None

    @callback
    def _client_changed(self) -> None:
        self._fire()

    def _fire(self) -> None:
        for cb in list(self._listeners):
            cb()

    # ---- naming --------------------------------------------------------------
    @property
    def num_zones(self) -> int:
        return self.client.state.spec.zones

    def inputs(self) -> list[InputDef]:
        return self.client.inputs()

    def input_name(self, source: int) -> str:
        if source == 0:
            return "Disconnected"
        name = self.settings["inputs"].get(str(source))
        if name:
            return name
        for inp in self.inputs():
            if inp.source == source:
                return inp.default_name
        return f"Source {source}"

    def zone_name(self, zone: int) -> str:
        return self.settings["outputs"].get(str(zone)) or f"Zone {zone}"

    def visible_inputs(self) -> list[InputDef]:
        hidden = set(self.settings["hidden_inputs"])
        return [i for i in self.inputs() if i.source not in hidden]

    def source_by_name(self, name: str) -> int:
        for inp in self.inputs():
            if self.input_name(inp.source) == name:
                return inp.source
        if name in ("Disconnected", "None", "Off"):
            return 0
        raise ServiceValidationError(f"Unknown ProAudio source '{name}'")

    async def async_set_names(
        self,
        inputs: dict[str, str] | None = None,
        outputs: dict[str, str] | None = None,
        hidden_inputs: list[int] | None = None,
        hidden_outputs: list[int] | None = None,
    ) -> None:
        for key, values in (("inputs", inputs), ("outputs", outputs)):
            if values is None:
                continue
            for num, name in values.items():
                name = (name or "").strip()
                if name:
                    self.settings[key][str(int(num))] = name
                else:
                    self.settings[key].pop(str(int(num)), None)
        if hidden_inputs is not None:
            self.settings["hidden_inputs"] = sorted({int(x) for x in hidden_inputs})
        if hidden_outputs is not None:
            self.settings["hidden_outputs"] = sorted({int(x) for x in hidden_outputs})
        await self.async_save()
        async_dispatcher_send(self.hass, SIGNAL_PRESETS_UPDATED.format(self.entry_id))
        self._fire()

    # ---- zone groups -----------------------------------------------------------
    @property
    def groups(self) -> list[dict[str, Any]]:
        return self.settings["groups"]

    async def async_save_groups(self, groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Replace all groups. A zone belongs to at most one group (first wins)."""
        seen: set[int] = set()
        clean: list[dict[str, Any]] = []
        for g in groups:
            name = str(g.get("name") or "").strip()
            if not name:
                continue
            zones = []
            for z in g.get("zones") or []:
                z = int(z)
                if 1 <= z <= self.num_zones and z not in seen:
                    seen.add(z)
                    zones.append(z)
            clean.append({"id": g.get("id") or uuid.uuid4().hex[:8], "name": name, "zones": sorted(zones)})
        self.settings["groups"] = clean
        await self.async_save()
        self._fire()
        return clean

    def group_zones(self, key: str) -> list[int]:
        for g in self.groups:
            if g["id"] == key or g["name"].casefold() == str(key).casefold():
                return list(g["zones"])
        raise ServiceValidationError(f"Unknown ProAudio zone group '{key}'")

    # ---- presets -------------------------------------------------------------
    @property
    def presets(self) -> list[dict[str, Any]]:
        return self.settings["presets"]

    def get_preset(self, key: str) -> dict[str, Any]:
        for p in self.presets:
            if p["id"] == key or p["name"].casefold() == str(key).casefold():
                return p
        raise ServiceValidationError(f"Unknown ProAudio preset '{key}'")

    async def async_save_preset(self, preset: dict[str, Any]) -> dict[str, Any]:
        routes = {str(int(z)): int(s) for z, s in (preset.get("routes") or {}).items()}
        if not routes:
            raise ServiceValidationError("A preset needs at least one zone")
        name = str(preset.get("name") or "Preset").strip()
        pid = preset.get("id")
        if not pid:  # a new preset with an existing name replaces that preset
            pid = next((p["id"] for p in self.presets if p["name"].casefold() == name.casefold()), None)
        clean = {
            "id": pid or uuid.uuid4().hex[:8],
            "name": name,
            "icon": preset.get("icon") or "mdi:playlist-play",
            "routes": routes,
            "power_on": bool(preset.get("power_on", True)),
            "unmute": bool(preset.get("unmute", True)),
            "volume": None if preset.get("volume") in (None, "") else max(0, min(100, int(preset["volume"]))),
            "disconnect_others": bool(preset.get("disconnect_others", False)),
        }
        for i, p in enumerate(self.presets):
            if p["id"] == clean["id"]:
                self.presets[i] = clean
                break
        else:
            self.presets.append(clean)
        await self.async_save()
        async_dispatcher_send(self.hass, SIGNAL_PRESETS_UPDATED.format(self.entry_id))
        self._fire()
        return clean

    async def async_delete_preset(self, preset_id: str) -> None:
        self.settings["presets"] = [p for p in self.presets if p["id"] != preset_id]
        await self.async_save()
        async_dispatcher_send(self.hass, SIGNAL_PRESETS_UPDATED.format(self.entry_id))
        self._fire()

    async def async_reorder_presets(self, ids: list[str]) -> None:
        order = {pid: i for i, pid in enumerate(ids)}
        self.presets.sort(key=lambda p: order.get(p["id"], len(order)))
        await self.async_save()
        self._fire()

    async def async_apply_preset(self, key: str) -> None:
        preset = self.get_preset(key)
        routes = {int(z): int(s) for z, s in preset["routes"].items()}
        by_source: dict[int, list[int]] = {}
        for zone, source in routes.items():
            by_source.setdefault(source, []).append(zone)
        await self._run(self._apply(preset, routes, by_source))

    async def _apply(self, preset, routes, by_source) -> None:
        c = self.client
        if not c.state.is_on:
            await c.set_power(True)
        if preset.get("disconnect_others"):
            sources = {s for s in by_source if s}
            others = [z for z, zs in c.state.zones.items() if zs.source in sources and z not in routes]
            if others:
                await c.route(others, 0)
        for source, zones in by_source.items():
            await c.route(zones, source)
        active = [z for z, s in routes.items() if s]
        if active and preset.get("power_on"):
            await c.set_zone_power(active, True)
        if active and preset.get("volume") is not None:
            await c.set_zone_volume(active, preset["volume"])
        if active and preset.get("unmute"):
            await c.set_zone_mute(active, False)

    # ---- control wrapper -----------------------------------------------------
    async def _run(self, coro) -> Any:
        try:
            return await coro
        except ProAudioError as err:
            raise HomeAssistantError(f"ProAudio: {err}") from err

    async def route(self, zones: list[int], source: int) -> None:
        self._check_zones(zones)
        await self._run(self.client.route(zones, source))

    async def clear_all(self) -> None:
        await self._run(self.client.clear_all())

    async def zone_power(self, zones: list[int], on: bool) -> None:
        self._check_zones(zones)
        await self._run(self.client.set_zone_power(zones, on))

    async def zone_mute(self, zones: list[int], mute: bool) -> None:
        self._check_zones(zones)
        await self._run(self.client.set_zone_mute(zones, mute))

    async def zone_volume(self, zones: list[int], volume: int) -> None:
        self._check_zones(zones)
        await self._run(self.client.set_zone_volume(zones, volume))

    async def master_volume(self, raw: int) -> None:
        await self._run(self.client.set_master_volume(raw))

    async def unit_power(self, on: bool) -> None:
        await self._run(self.client.set_power(on))

    async def refresh(self) -> None:
        await self._run(self.client.refresh(full=True))

    def _check_zones(self, zones: list[int]) -> None:
        bad = [z for z in zones if not 1 <= int(z) <= self.num_zones]
        if bad or not zones:
            raise ServiceValidationError(f"Invalid zone(s) {bad or zones} (1-{self.num_zones})")

    # ---- snapshot for the panel ------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        s = self.client.state
        hidden_in = set(self.settings["hidden_inputs"])
        hidden_out = set(self.settings["hidden_outputs"])
        zones_by_source: dict[int, list[int]] = {}
        for z in range(1, self.num_zones + 1):
            zs = s.zones.get(z)
            if zs and zs.source:
                zones_by_source.setdefault(zs.source, []).append(z)

        inputs = []
        for inp in self.inputs():
            fed = zones_by_source.get(inp.source, [])
            signal = None
            if inp.kind != "analog":
                types = {s.zones[z].audio_type for z in fed if s.zones[z].audio_type is not None}
                if types:
                    signal = AUDIO_TYPES.get(max(types))
            inputs.append({
                "source": inp.source, "kind": inp.kind, "index": inp.index,
                "name": self.input_name(inp.source), "default_name": inp.default_name,
                "custom_name": self.settings["inputs"].get(str(inp.source)),
                "hidden": inp.source in hidden_in, "zones": fed, "signal": signal,
            })
        outputs = []
        for z in range(1, self.num_zones + 1):
            zs = s.zones.get(z)
            outputs.append({
                "zone": z, "name": self.zone_name(z),
                "custom_name": self.settings["outputs"].get(str(z)),
                "hidden": z in hidden_out,
                "source": zs.source if zs else None,
                "power": zs.power if zs else None,
                "muted": zs.muted if zs else None,
                "hard_muted": zs.hard_muted if zs else None,
                "volume": zs.volume if zs else None,
                "audio_type": AUDIO_TYPES.get(zs.audio_type) if zs and zs.audio_type is not None else None,
            })
        xs = s.xs1 or 0
        return {
            "entry_id": self.entry_id,
            "title": self.title,
            "connected": s.connected,
            "host": self.client.host,
            "port": self.client.port,
            "model": s.model,
            "firmware": s.firmware,
            "serial": s.serial,
            "power": s.power,
            "master_volume": s.master_volume,
            "master_db": master_db(s.master_volume),
            "ip": dict(s.ip),
            "xs": None if s.xs1 is None else {
                "raw": [s.xs1, s.xs2], "asy": bool(xs & 1), "ack": bool(xs & 2),
                "eco": bool(xs & 4), "cre": bool(xs & 16), "xio": bool(xs & 32768),
            },
            "zone_count": self.num_zones,
            "last_update": s.last_update,
            "server_time": time.time(),
            "errors": list(s.errors),
            "inputs": inputs,
            "outputs": outputs,
            "presets": self.presets,
            "groups": self.groups,
        }
