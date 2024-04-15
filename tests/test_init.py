"""Tests for Magic Areas integration."""

from custom_components.magic_areas.util import basic_area_from_object
from custom_components.magic_areas.const import (
    DOMAIN,
    MODULE_DATA,
    _DOMAIN_SCHEMA,
    DATA_UNDO_UPDATE_LISTENER,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_NAME, CONF_ID

from pytest_homeassistant_custom_component.common import MockConfigEntry

import logging
import time

LOGGER = logging.getLogger(__name__)

MOCK_AREA_NAME = 'MagicAreas Test Area'

async def test_successful_config_entry(hass):
    """Test that Magic Areas is configured successfully."""

    # Find out the first available area
    area_registry = hass.helpers.area_registry.async_get(hass)
    mock_area = area_registry.async_get_or_create(MOCK_AREA_NAME)

    assert mock_area is not None

    LOGGER.info("Got mock area: %s", mock_area.name)

    config_entry_data = _DOMAIN_SCHEMA({f"{mock_area.id}": {}})[mock_area.id]
    extra_opts = {
                CONF_ID: mock_area.id,
                CONF_NAME: mock_area.name
            }
    config_entry_data.update(extra_opts)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_entry_data,
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.LOADED

    assert DATA_UNDO_UPDATE_LISTENER in hass.data[MODULE_DATA][entry.entry_id]


async def test_unload_entry(hass):
    """Test removing Magic Areas."""

    # Find out the first available area
    area_registry = hass.helpers.area_registry.async_get(hass)
    mock_area = area_registry.async_get_or_create(MOCK_AREA_NAME)

    assert mock_area is not None

    LOGGER.info("Got mock area: %s", mock_area.name)

    config_entry_data = _DOMAIN_SCHEMA({f"{mock_area.id}": {}})[mock_area.id]
    extra_opts = {
                CONF_ID: mock_area.id,
                CONF_NAME: mock_area.name
            }
    config_entry_data.update(extra_opts)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_entry_data,
    )

    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state == ConfigEntryState.NOT_LOADED
    assert MODULE_DATA not in hass.data