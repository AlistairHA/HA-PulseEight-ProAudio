"""Config flow for Pulse-Eight ProAudio."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback

from .client import DEFAULT_PORT, ProAudioError, probe
from .const import CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL, DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
    }
)


class ProAudioConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _probe(self, data: dict[str, Any]):
        try:
            return await probe(data[CONF_HOST].strip(), data[CONF_PORT]), {}
        except ProAudioError:
            return None, {"base": "cannot_connect"}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            state, errors = await self._probe(user_input)
            if state is not None:
                host = user_input[CONF_HOST].strip()
                await self.async_set_unique_id(state.serial or f"{host}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: user_input[CONF_PORT]})
                return self.async_create_entry(
                    title=state.model or "ProAudio",
                    data={CONF_HOST: host, CONF_PORT: user_input[CONF_PORT]},
                )
        return self.async_show_form(
            step_id="user", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input), errors=errors
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            state, errors = await self._probe(user_input)
            if state is not None:
                if state.serial:
                    await self.async_set_unique_id(state.serial)
                    self._abort_if_unique_id_mismatch(reason="wrong_device")
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: user_input[CONF_HOST].strip(), CONF_PORT: user_input[CONF_PORT]}
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or dict(entry.data)),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return ProAudioOptionsFlow()


class ProAudioOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=self.config_entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): vol.All(vol.Coerce(int), vol.Range(min=5, max=600))
                }
            ),
        )
