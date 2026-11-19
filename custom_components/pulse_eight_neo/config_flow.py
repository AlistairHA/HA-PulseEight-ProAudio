"""Config flow for Pulse-Eight neo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.core import callback

from .client import MODELS, NeoAuthError, NeoClient, NeoError, first
from .const import CONF_DETAIL_INTERVAL, CONF_SCAN_INTERVAL, DEFAULT_DETAIL_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

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
    if not first(d, "Serial"):
        return None, {"base": "not_neo"}
    return d, {}


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
        }))
