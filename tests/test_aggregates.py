"""Test for aggregate (group) sensor behavior."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON, UnitOfTemperature, UnitOfElectricCurrent

from random import randint
from statistics import mean

from .mocks import MockBinarySensor, MockSensor

_LOGGER = logging.getLogger(__name__)

async def test_aggregates_binary_sensor_regular(
    hass: HomeAssistant,
    entities_binary_sensor_motion_multiple: list[MockBinarySensor],
    _setup_integration_aggregates,
) -> None:
    """Test binary sensor aggregates with all=False."""

    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_motion"
    )

    # Init test & individual ON/OFF flip
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert aggregate_sensor_state.state == STATE_OFF

    for mock_entity in entities_binary_sensor_motion_multiple:
        assert mock_entity.entity_id in aggregate_sensor_state.attributes['entity_id']

        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_OFF

        # Test state flip ON
        hass.states.async_set(mock_entity.entity_id, STATE_ON)
        await hass.async_block_till_done()
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_ON
        aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
        assert aggregate_sensor_state.state == STATE_ON

        # Test state flip OFF
        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_OFF
        aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
        assert aggregate_sensor_state.state == STATE_OFF

    # Turn all ON
    for mock_entity in entities_binary_sensor_motion_multiple:
        hass.states.async_set(mock_entity.entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Turn all off and ensure only off when last off
    for entity_index, mock_entity in enumerate(entities_binary_sensor_motion_multiple):

        last_sensor = (entity_index == (len(entities_binary_sensor_motion_multiple)-1))
        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        aggregate_sensor_state = hass.states.get(aggregate_sensor_id)

        if last_sensor:
            assert aggregate_sensor_state.state == STATE_OFF
        else:
            assert aggregate_sensor_state.state == STATE_ON

async def test_aggregates_binary_sensor_all(
    hass: HomeAssistant,
    entities_binary_sensor_connectivity_multiple: list[MockBinarySensor],
    _setup_integration_aggregates,
) -> None:
    """Test binary sensor aggregates with all=True."""

    aggregate_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_connectivity"
    )

    # Init test
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert aggregate_sensor_state.state == STATE_OFF

    # ON test
    for entity_index, mock_entity in enumerate(entities_binary_sensor_connectivity_multiple):

        last_sensor = (entity_index == (len(entities_binary_sensor_connectivity_multiple)-1))

        assert mock_entity.entity_id in aggregate_sensor_state.attributes['entity_id']

        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_OFF

        # Test state flip ON
        hass.states.async_set(mock_entity.entity_id, STATE_ON)
        await hass.async_block_till_done()
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_ON
        aggregate_sensor_state = hass.states.get(aggregate_sensor_id)

        if last_sensor:
            assert aggregate_sensor_state.state == STATE_ON
        else:
            assert aggregate_sensor_state.state == STATE_OFF

    # OFF test
    for entity_index, mock_entity in enumerate(entities_binary_sensor_connectivity_multiple):

        last_sensor = (entity_index == (len(entities_binary_sensor_connectivity_multiple)-1))

         # Test state flip OFF
        hass.states.async_set(mock_entity.entity_id, STATE_OFF)
        await hass.async_block_till_done()
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state.state == STATE_OFF
        aggregate_sensor_state = hass.states.get(aggregate_sensor_id)

        assert aggregate_sensor_state.state == STATE_OFF

async def test_aggregates_sensor_avg(
    hass: HomeAssistant,
    entities_sensor_temperature_multiple: list[MockSensor],
    _setup_integration_aggregates,
) -> None:
    """Test binary sensor aggregates with all=True."""

    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_temperature"
    )

    _LOGGER.warning(entities_sensor_temperature_multiple)

    entity_values = []

    # Read initial values
    for mock_entity in entities_sensor_temperature_multiple:
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state is not None
        entity_values.append(int(mock_state.state))

    # Init test
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(mean(entity_values), 2)

    # Change all the values
    changed_values = []
    for mock_entity in entities_sensor_temperature_multiple:
        random_value = randint(0, 100)
        changed_values.append(random_value)
        hass.states.async_set(mock_entity.entity_id, random_value, attributes={'unit_of_measurement': UnitOfTemperature.CELSIUS})
        await hass.async_block_till_done()
        changed_state = hass.states.get(mock_entity.entity_id)
        assert int(changed_state.state) == random_value

    # Check changed values
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(mean(changed_values), 2)

async def test_aggregates_sensor_sum(
    hass: HomeAssistant,
    entities_sensor_current_multiple: list[MockSensor],
    _setup_integration_aggregates,
) -> None:
    """Test binary sensor aggregates with all=True."""

    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_current"
    )

    _LOGGER.warning(entities_sensor_current_multiple)

    entity_values = []

    # Read initial values
    for mock_entity in entities_sensor_current_multiple:
        mock_state = hass.states.get(mock_entity.entity_id)
        assert mock_state is not None
        entity_values.append(int(mock_state.state))

    # Init test
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(sum(entity_values), 2)

    # Change all the values
    changed_values = []
    for mock_entity in entities_sensor_current_multiple:
        random_value = randint(0, 100)
        changed_values.append(random_value)
        hass.states.async_set(mock_entity.entity_id, random_value, attributes={'unit_of_measurement': UnitOfElectricCurrent.AMPERE})
        await hass.async_block_till_done()
        changed_state = hass.states.get(mock_entity.entity_id)
        assert int(changed_state.state) == random_value

    # Check changed values
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert round(float(aggregate_sensor_state.state), 2) == round(sum(changed_values), 2)
