"""Test for climate groups."""

import logging
import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN

from tests.const import DEFAULT_MOCK_AREA

from .mocks import MockClimate

_LOGGER = logging.getLogger(__name__)


async def test_climate_group_basic(
    hass: HomeAssistant,
    entities_climate_group_one: list[MockClimate],
    _setup_integration_climate_groups,
) -> None:
    """Test climate group."""

    mock_climate_entity_id = f"{CLIMATE_DOMAIN}.climate_1"
    climate_group_entity_id = (
        f"{CLIMATE_DOMAIN}.magic_areas_climate_groups_{DEFAULT_MOCK_AREA}_climate_group"
    )
    climate_control_entity_id = f"{SWITCH_DOMAIN}.magic_areas_climate_groups_{DEFAULT_MOCK_AREA}_climate_control"
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    presence_hold_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"
    )

    # Test mock entity created
    mock_climate_state = hass.states.get(mock_climate_entity_id)
    assert mock_climate_state is not None
    assert mock_climate_state.state == STATE_OFF

    # Test climate group created
    climate_group_state = hass.states.get(climate_group_entity_id)
    assert climate_group_state is not None
    assert climate_group_state.state == STATE_OFF

    # Test climate control switch created
    climate_control_state = hass.states.get(climate_control_entity_id)
    assert climate_control_state is not None
    assert climate_control_state.state == STATE_OFF

    # Test presence hold switch created
    presence_hold_state = hass.states.get(presence_hold_entity_id)
    assert presence_hold_state is not None
    assert presence_hold_state.state == STATE_OFF

    # Test area state
    area_state = hass.states.get(area_sensor_entity_id)
    assert area_state is not None
    assert area_state.state == STATE_OFF

    # Turn on climate control
    hass.states.async_set(climate_control_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test climate control switch state turned on
    climate_control_state = hass.states.get(climate_control_entity_id)
    assert climate_control_state is not None
    assert climate_control_state.state == STATE_ON

    # Turn area occupied through presence hold
    hass.states.async_set(presence_hold_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test area state is STATE_ON
    area_state = hass.states.get(area_sensor_entity_id)
    assert area_state is not None
    assert area_state.state == STATE_ON

    # # Sleep so climate group has a chance to react
    # await asyncio.sleep(1)
    # await hass.async_block_till_done()

    # hass.states.async_set(climate_group_entity_id, STATE_ON)
    # await hass.async_block_till_done()

    # # Test climate group is STATE_ON
    # climate_group_state = hass.states.get(climate_group_entity_id)
    # assert climate_group_state is not None
    # assert climate_group_state.state == STATE_ON

    # # Test mock entity is STATE_ON
    # mock_climate_state = hass.states.get(mock_climate_entity_id)
    # assert mock_climate_state is not None
    # assert mock_climate_state.state == STATE_ON
