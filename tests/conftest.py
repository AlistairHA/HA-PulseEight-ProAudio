"""Fixtures for ProAudio tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pulse_eight_proaudio.const import DOMAIN

from .fake_proaudio import FakeProAudio


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations, socket_enabled):
    yield


@pytest.fixture
def fake_kwargs() -> dict:
    return {}


@pytest.fixture
async def fake(fake_kwargs):
    unit = FakeProAudio(**fake_kwargs)
    unit.port = await unit.start()
    yield unit
    await unit.stop()


@pytest.fixture
def entry(fake) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="ProAudio32", unique_id="59B2S12345678",
        data={"host": "127.0.0.1", "port": fake.port},
    )


@pytest.fixture
async def loaded(hass, entry):
    await __import__("homeassistant.setup", fromlist=["x"]).async_setup_component(hass, "http", {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
