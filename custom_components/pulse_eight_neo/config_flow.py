"""Config flow for Pulse-Eight neo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo

from .client import MODELS, NeoAuthError, NeoClient, NeoError, first
from .const import (
    CONF_DETAIL_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_UDP,
    CONF_UDP_PORT,
    DEFAULT_DETAIL_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UDP,
    DEFAULT_UDP_PORT,
    DOMAIN,
)

SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Optional(CONF_PASSWORD, default=""): str})


async def _probe(host: str, password: str) -> tuple[dict | None, dict[str, str]]:
    client = NeoClient(host, password, timeout=10)
    try:
        d = await client.details()
        await client.ports()  # proves read access (some firmware needs login for this)
    except NeoAuthError:
        return None, {"base": "invalid_auth"}
    except NeoError:
        return None, {"base": "cannot_connect"}
    finally:
        await client.close()
    if not first(d, "Serial") or not is_matrix(str(first(d, "Model", default=""))):
        return None, {"base": "not_neo"}
    return d, {}


def is_matrix(model: str) -> bool:
    """neo matrices are FFxx / MMxx models; ProAmp8 and ProAudio share the vendor MAC prefix."""
    m = model.upper()
    return m in MODELS or m.startswith(("FF", "MM"))


class NeoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            d, errors = await _probe(host, user_input.get(CONF_PASSWORD, ""))
            if d:
                await self.async_set_unique_id(str(first(d, "Serial")))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                model = MODELS.get(str(first(d, "Model", default="")), "neo matrix")
                return self.async_create_entry(title=model, data={CONF_HOST: host, CONF_PASSWORD: user_input.get(CONF_PASSWORD, "")})
        return self.async_show_form(step_id="user", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input), errors=errors)

    async def async_step_dhcp(self, discovery_info: DhcpServiceInfo) -> ConfigFlowResult:
        host = discovery_info.ip
        client = NeoClient(host, "", timeout=10)
        try:
            d = await client.details()
        except NeoError:
            return self.async_abort(reason="cannot_connect")
        finally:
            await client.close()
        serial, model = first(d, "Serial"), str(first(d, "Model", default=""))
        if not serial or not is_matrix(model):
            return self.async_abort(reason="not_neo")
        await self.async_set_unique_id(str(serial))
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._disc = {CONF_HOST: host, "model": MODELS.get(model, "neo matrix")}
        self.context["title_placeholders"] = {"name": f"{self._disc['model']} ({host})"}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        host = self._disc[CONF_HOST]
        if user_input is not None:
            d, errors = await _probe(host, user_input.get(CONF_PASSWORD, ""))
            if d:
                return self.async_create_entry(title=self._disc["model"], data={CONF_HOST: host, CONF_PASSWORD: user_input.get(CONF_PASSWORD, "")})
        return self.async_show_form(step_id="discovery_confirm", data_schema=vol.Schema({vol.Optional(CONF_PASSWORD, default=""): str}),
                                    description_placeholders={"model": self._disc["model"], "host": host}, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            d, errors = await _probe(entry.data[CONF_HOST], user_input[CONF_PASSWORD])
            if d:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}), errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            d, errors = await _probe(user_input[CONF_HOST].strip(), user_input.get(CONF_PASSWORD, ""))
            if d:
                await self.async_set_unique_id(str(first(d, "Serial")))
                self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(entry, data_updates={CONF_HOST: user_input[CONF_HOST].strip(), CONF_PASSWORD: user_input.get(CONF_PASSWORD, "")})
        return self.async_show_form(step_id="reconfigure", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or dict(entry.data)), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return NeoOptionsFlow()


class NeoOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        o = self.config_entry.options
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=2, max=120)),
            vol.Required(CONF_DETAIL_INTERVAL, default=o.get(CONF_DETAIL_INTERVAL, DEFAULT_DETAIL_INTERVAL)): vol.All(vol.Coerce(int), vol.Range(min=20, max=3600)),
            vol.Required(CONF_UDP, default=o.get(CONF_UDP, DEFAULT_UDP)): bool,
            vol.Required(CONF_UDP_PORT, default=o.get(CONF_UDP_PORT, DEFAULT_UDP_PORT)): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        }))
