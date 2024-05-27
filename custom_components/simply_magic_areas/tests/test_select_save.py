"""Test for saving the entity."""

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from ..const import DOMAIN, AreaState

_LOGGER = logging.getLogger(__name__)


async def test_save_select(
    hass: HomeAssistant, config_entry: MockConfigEntry, _setup_integration
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == "clear"
    assert area_binary_sensor.attributes == {
        "active_sensors": [],
        "friendly_name": "Simply Magic Areas (kitchen)",
        "icon": "mdi:home-search",
        "last_active_sensors": [],
        "presence_sensors": [],
        "state": AreaState.AREA_STATE_CLEAR,
        "type": "interior",
        "options": [
            AreaState.AREA_STATE_CLEAR,
            AreaState.AREA_STATE_OCCUPIED,
            AreaState.AREA_STATE_EXTENDED,
            AreaState.AREA_STATE_BRIGHT,
            AreaState.AREA_STATE_SLEEP,
            AreaState.AREA_STATE_ACCENTED,
        ],
    }

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
