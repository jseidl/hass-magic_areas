"""Test for area changes and how the system handles it."""

import logging
import asyncio

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er

from .mocks import MockBinarySensor

_LOGGER = logging.getLogger(__name__)


#@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_area_change(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_motion: list[MockBinarySensor],
    _setup_integration,
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    motion_sensor_entity_id = one_motion[0].entity_id
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(area_sensor_entity_id)

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == STATE_OFF

    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor.state == STATE_ON
    assert area_binary_sensor.state == STATE_ON

    # Turn off motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    #asyncio.sleep(5) @FIXME once I get the timers fixed call_later -> async_call_later

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor.state == STATE_OFF
    assert area_binary_sensor.state == STATE_OFF