from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pulse_eight_neo.const import DOMAIN

from .fake_neo import FakeNeo


@pytest.fixture(autouse=True)
def auto_enable(enable_custom_integrations, socket_enabled):
    yield


@pytest.fixture
def fake_kwargs():
    return {}


@pytest.fixture
async def fake(fake_kwargs):
    f = FakeNeo(**fake_kwargs)
    f.port = await f.start()
    yield f
    await f.stop()


@pytest.fixture
def entry_options():
    return {"udp_push": False}


@pytest.fixture
def entry(fake, entry_options):
    return MockConfigEntry(domain=DOMAIN, title="neo:X+", unique_id="P8SN0123456",
                           data={"host": f"127.0.0.1:{fake.port}", "password": fake.password},
                           options=entry_options)


@pytest.fixture
async def loaded(hass, entry):
    from homeassistant.setup import async_setup_component
    await async_setup_component(hass, "http", {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
