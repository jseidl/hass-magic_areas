"""Tests for Magic Areas primary state change."""

import logging

from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, ATTR_ENTITY_ID, STATE_ON, STATE_OFF

from .common import setup_area_with_presence_sensor
from .const import NOCK_PRESENCE_INPUT_BOOLEAN_ID, NOCK_PRESENCE_BINARY_SENSOR_ID, MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID

LOGGER = logging.getLogger(__name__)

async def test_primary_state_change(hass):
    """Test that Magic Areas presence sensor is correctly tracking presence."""

    entry = await setup_area_with_presence_sensor(hass)
    assert hass.states.get(NOCK_PRESENCE_BINARY_SENSOR_ID).state == STATE_OFF

    # Flip input boolean on
    await hass.services.async_call(
        INPUT_BOOLEAN_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: NOCK_PRESENCE_INPUT_BOOLEAN_ID},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check both binary sensor and area sensor turned on
    assert hass.states.get(NOCK_PRESENCE_BINARY_SENSOR_ID).state == STATE_ON
    assert hass.states.get(MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID).state == STATE_ON