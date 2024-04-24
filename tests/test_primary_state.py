"""Tests for Magic Areas primary state change."""

from asyncio import sleep
import logging

from custom_components.magic_areas.const import CONF_CLEAR_TIMEOUT, CONF_UPDATE_INTERVAL
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)

from .common import setup_area_with_presence_sensor
from .const import (
    MOCK_AREA_CLEAR_TIMEOUT,
    MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID,
    NOCK_PRESENCE_BINARY_SENSOR_ID,
    NOCK_PRESENCE_INPUT_BOOLEAN_ID,
)

LOGGER = logging.getLogger(__name__)


async def test_primary_state_change(hass):
    """Test that Magic Areas presence sensor is correctly tracking presence."""

    extra_opts = {
        CONF_CLEAR_TIMEOUT: MOCK_AREA_CLEAR_TIMEOUT,
        CONF_UPDATE_INTERVAL: MOCK_AREA_CLEAR_TIMEOUT,
    }

    await setup_area_with_presence_sensor(hass, extra_opts)
    assert hass.states.get(NOCK_PRESENCE_BINARY_SENSOR_ID).state == STATE_OFF

    # ON TEST
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

    # Sleep briefly to allow async to catch up
    await hass.async_block_till_done()
    assert hass.states.get(MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID).state == STATE_ON

    # OFF TEST
    # Flip input boolean on
    await hass.async_block_till_done()
    await hass.services.async_call(
        INPUT_BOOLEAN_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: NOCK_PRESENCE_INPUT_BOOLEAN_ID},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check both binary sensor and area sensor turned on
    assert hass.states.get(NOCK_PRESENCE_BINARY_SENSOR_ID).state == STATE_OFF

    # Give time for clear timeout, a bit longer than configured
    await sleep(MOCK_AREA_CLEAR_TIMEOUT * 1.1)

    # Sleep briefly to allow async to catch up
    await hass.async_block_till_done()
    assert hass.states.get(MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID).state == STATE_OFF
