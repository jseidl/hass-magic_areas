"""Test for area changes and how the system handles it."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .mocks import MockBinarySensor
from custom_components.magic_areas.const import AreaStates

_LOGGER = logging.getLogger(__name__)


async def test_area_primary_state_change(
    hass: HomeAssistant,
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration,
) -> None:
    """Test primary area state change."""

    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(area_sensor_entity_id)

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == STATE_OFF
    assert motion_sensor_entity_id in area_binary_sensor.attributes["presence_sensors"]
    assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]

    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor is not None
    assert area_binary_sensor is not None
    assert motion_sensor.state == STATE_ON
    assert area_binary_sensor.state == STATE_ON
    assert AreaStates.OCCUPIED in area_binary_sensor.attributes["states"]

    # Turn off motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # @FIXME figure out why this is blocking instead of doing the VirtualClock trick
    # await asyncio.sleep(60)
    # await hass.async_block_till_done()

    # Update states
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor is not None
    assert area_binary_sensor is not None
    assert motion_sensor.state == STATE_OFF
    assert area_binary_sensor.state == STATE_OFF
    assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]


async def test_area_secondary_state_change(
    hass: HomeAssistant,
    secondary_states_sensors: list[MockBinarySensor],
    _setup_integration_secondary_states,
) -> None:
    """Test secondary area state changes."""

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    secondary_state_map = {
        secondary_states_sensors[0].entity_id: (AreaStates.SLEEP, None),
        secondary_states_sensors[1].entity_id: (AreaStates.BRIGHT, AreaStates.DARK),
        secondary_states_sensors[2].entity_id: (AreaStates.ACCENT, None),
    }

    for entity_id, state_tuples in secondary_state_map.items():
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure off
        assert entity_state is not None
        assert area_binary_sensor is not None
        assert entity_state.state == STATE_OFF
        assert state_tuples[0] not in area_binary_sensor.attributes["states"]
        if state_tuples[1]:
            assert state_tuples[1] in area_binary_sensor.attributes["states"]

        # Turn entity on
        hass.states.async_set(entity_id, STATE_ON)
        await hass.async_block_till_done()

        # Update states
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure on
        assert entity_state is not None
        assert area_binary_sensor is not None
        assert entity_state.state == STATE_ON
        assert state_tuples[0] in area_binary_sensor.attributes["states"]
        if state_tuples[1]:
            assert state_tuples[1] not in area_binary_sensor.attributes["states"]

        # Turn entity off
        hass.states.async_set(entity_id, STATE_OFF)
        await hass.async_block_till_done()

        # Update states
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        entity_state = hass.states.get(entity_id)

        # Ensure off
        assert entity_state is not None
        assert area_binary_sensor is not None
        assert entity_state.state == STATE_OFF
        assert state_tuples[0] not in area_binary_sensor.attributes["states"]
        if state_tuples[1]:
            assert state_tuples[1] in area_binary_sensor.attributes["states"]


# Test extended state
# @TODO pending figuring out virtualclock


# Test keep-only sensors
async def test_keep_only_sensors(
    hass: HomeAssistant,
    entities_binary_sensor_motion_multiple: list[MockBinarySensor],
    _setup_integration_keep_only_sensor,
) -> None:
    """Test keep-only sensors."""

    motion_sensor_entity_id = entities_binary_sensor_motion_multiple[0].entity_id
    flappy_sensor_entity_id = entities_binary_sensor_motion_multiple[1].entity_id
    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(area_sensor_entity_id)

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == STATE_OFF
    assert motion_sensor_entity_id in area_binary_sensor.attributes["presence_sensors"]
    assert flappy_sensor_entity_id in area_binary_sensor.attributes["presence_sensors"]
    assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]

    # Turn on flappy sensor
    hass.states.async_set(flappy_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states, ensure area remains clear
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    flappy_sensor = hass.states.get(flappy_sensor_entity_id)

    assert flappy_sensor is not None
    assert area_binary_sensor is not None
    assert flappy_sensor.state == STATE_ON
    assert area_binary_sensor.state == STATE_OFF
    assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]

    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Update states, ensure area is now occupied
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor is not None
    assert area_binary_sensor is not None
    assert motion_sensor.state == STATE_ON
    assert area_binary_sensor.state == STATE_ON
    assert AreaStates.OCCUPIED in area_binary_sensor.attributes["states"]

    # Turn off motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # Update states, ensure area remains occupied
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor is not None
    assert area_binary_sensor is not None
    assert motion_sensor.state == STATE_OFF
    assert area_binary_sensor.state == STATE_ON
    assert AreaStates.OCCUPIED in area_binary_sensor.attributes["states"]

    # Turn off flappy sensor
    hass.states.async_set(flappy_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    # Update states, ensure area clears
    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    flappy_sensor = hass.states.get(flappy_sensor_entity_id)

    assert motion_sensor is not None
    assert area_binary_sensor is not None
    assert flappy_sensor is not None
    assert flappy_sensor.state == STATE_OFF
    assert area_binary_sensor.state == STATE_OFF
    assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]
