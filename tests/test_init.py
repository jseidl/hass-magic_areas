"""Tests for Magic Areas integration load and unload."""

import logging

from custom_components.magic_areas.const import DATA_UNDO_UPDATE_LISTENER, MODULE_DATA
from homeassistant.config_entries import ConfigEntryState

from .common import setup_area
from .const import MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID

LOGGER = logging.getLogger(__name__)


async def test_successful_config_entry(hass):
    """Test that Magic Areas is configured successfully."""

    entry = await setup_area(hass)

    assert entry.state == ConfigEntryState.LOADED

    assert MODULE_DATA in hass.data
    assert DATA_UNDO_UPDATE_LISTENER in hass.data[MODULE_DATA][entry.entry_id]

    assert hass.states.get(MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID)


async def test_unload_entry(hass):
    """Test removing Magic Areas."""

    entry = await setup_area(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert MODULE_DATA not in hass.data

    # @FIXME seems like MA is not removing entity? (going to unavailable).
    # Unsure if that's "normal" or if the entity should indeed be missing
    # assert hass.states.get(MOCK_PRESENCE_SENSOR_ENTITY_ID) is None
