"""Sensors: unit status/identity/temperatures, and per-output HDBaseT link details."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfElectricCurrent, UnitOfElectricPotential, UnitOfLength, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import NeoConfigEntry
from .client import first, link_quality
from .entity import NeoEntity, NeoOutputEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: NeoConfigEntry, add: AddConfigEntryEntitiesCallback) -> None:
    hub = entry.runtime_data
    ents: list[SensorEntity] = [UnitSensor(hub, k) for k in ("status", "model", "firmware", "serial")]
    ents += [Temperature(hub, k) for k, _ in sorted((k[11:], v) for k, v in hub.health.items() if k.startswith("Temperature") and k[11:].isdigit())]
    if first(hub.health, "Uptime") is not None:
        ents.append(LastBoot(hub))
    ents += [PowerSupply(hub, i) for i in range(len(hub.psu))]
    ents.append(LastPush(hub))
    for b in sorted(hub.outputs):
        ents.append(OutputSignal(hub, b))
        if hub.is_hdbt(b):
            ents += [LinkStatus(hub, b), LinkQuality(hub, b), CableLength(hub, b)]
    add(ents)


class UnitSensor(NeoEntity, SensorEntity):
    def __init__(self, hub, key: str) -> None:
        super().__init__(hub, key)
        self.key = key
        self._attr_translation_key = key
        if key != "status":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        h = self.hub
        return {"status": first(h.health, "StatusMessage", default=first(h.details, "StatusMessage")),
                "model": h.model_name, "firmware": first(h.details, "Version"), "serial": h.serial}[self.key]

    @property
    def extra_state_attributes(self):
        if self.key == "status":
            return {k: v for k, v in self.hub.health.items() if k != "Result" and not k.startswith("Temperature") and not isinstance(v, (dict, list))}
        if self.key == "model":
            return {"model_code": self.hub.model_code}
        return None


class Temperature(NeoEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "temperature"

    def __init__(self, hub, idx: str) -> None:
        super().__init__(hub, f"temperature_{idx}")
        self.idx = idx
        self._attr_translation_placeholders = {"index": str(int(idx) + 1)}

    @property
    def native_value(self):
        return first(self.hub.health, f"Temperature{self.idx}")


class LastBoot(NeoEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_boot"
    _boot: datetime | None = None

    def __init__(self, hub) -> None:
        super().__init__(hub, "last_boot")

    @property
    def native_value(self):
        try:
            boot = (dt_util.utcnow() - timedelta(seconds=float(first(self.hub.health, "Uptime")))).replace(microsecond=0)
        except (TypeError, ValueError):
            return self._boot
        if self._boot is None or abs((boot - self._boot).total_seconds()) > 120:
            self._boot = boot
        return self._boot


class OutputSignal(NeoOutputEntity, SensorEntity):
    _attr_translation_key = "video_format"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "video_format")

    @property
    def native_value(self):
        return first(self.hub.out_details.get(self.bay), "Signal")

    @property
    def extra_state_attributes(self):
        d = self.hub.out_details.get(self.bay) or {}
        return {"display": first(d, "MonitorName"), "hdcp": first(d, "HDCP")}


class LinkStatus(NeoOutputEntity, SensorEntity):
    _attr_translation_key = "link_status"

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "link_status")

    @property
    def native_value(self):
        return first(self.hub.out_details.get(self.bay), "LinkStatus")

    @property
    def extra_state_attributes(self):
        r = self.hub.remote.get(self.bay) or {}
        return {f"receiver_{k.lower()}": v for k, v in r.items() if k != "Result" and not isinstance(v, (dict, list))}


class LinkQuality(NeoOutputEntity, SensorEntity):
    _attr_translation_key = "link_quality"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["good", "poor"]

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "link_quality")

    def _lq(self):
        return link_quality(first(self.hub.out_details.get(self.bay), "LinkQuality"))

    @property
    def native_value(self):
        lq = self._lq()
        r = lq and lq.get("rating")
        return r if r in ("good", "poor") else None

    @property
    def extra_state_attributes(self):
        lq = self._lq() or {}
        return {**{f"channel_{c.lower()}_db": v for c, v in (lq.get("channels") or {}).items()}, **{k: v for k, v in (lq.get("raw") or {}).items() if not k.startswith("Channel")}}


class CableLength(NeoOutputEntity, SensorEntity):
    _attr_translation_key = "cable_length"
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.METERS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hub, bay) -> None:
        super().__init__(hub, bay, "cable_length")

    @property
    def native_value(self):
        return first(self.hub.out_details.get(self.bay), "EstimatedCableLength")


class PowerSupply(NeoEntity, SensorEntity):
    """One reading from System/Health "psu" (named rail voltage or current)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "psu"

    def __init__(self, hub, idx: int) -> None:
        super().__init__(hub, f"psu_{idx}")
        self.idx = idx
        name = str(first(hub.psu[idx], "name", "Name", default=f"Supply {idx + 1}"))
        self._attr_translation_placeholders = {"name": name}
        if "current" in name.lower() or name.lower().endswith("a"):
            self._attr_device_class, self._attr_native_unit_of_measurement = SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE
        else:
            self._attr_device_class, self._attr_native_unit_of_measurement = SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT

    @property
    def native_value(self):
        psu = self.hub.psu
        return first(psu[self.idx], "value", "Value") if self.idx < len(psu) else None

    @property
    def extra_state_attributes(self):
        psu = self.hub.psu
        return {k: v for k, v in psu[self.idx].items() if k.lower() not in ("value", "name")} if self.idx < len(psu) else None


class LastPush(NeoEntity, SensorEntity):
    """When the last UDP state broadcast arrived (empty if pushes aren't reaching HA)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "last_push"
    _attr_entity_registry_enabled_default = False

    def __init__(self, hub) -> None:
        super().__init__(hub, "last_push")

    @property
    def native_value(self):
        return dt_util.utc_from_timestamp(self.hub.last_udp) if self.hub.last_udp else None

    @property
    def extra_state_attributes(self):
        return {"packets": self.hub.udp_packets}
