"""Test for Wasp in a box sensor behavior."""

import asyncio
from collections.abc import AsyncGenerator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from tests.common import assert_in_attribute, assert_state

from .conftest import (
    DEFAULT_MOCK_AREA,
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
)
from .mocks import MockBinarySensor
from custom_components.magic_areas.const import (
    ATTR_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_WASP_IN_A_BOX,
    CONF_WASP_IN_A_BOX_DELAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Fixtures


@pytest.fixture(name="wasp_in_a_box_config_entry")
def mock_config_entry_wasp_in_a_box() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_WASP_IN_A_BOX: {CONF_WASP_IN_A_BOX_DELAY: 0},
                CONF_FEATURE_AGGREGATION: {CONF_AGGREGATES_MIN_ENTITIES: 1},
            },
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_wasp_in_a_box")
async def setup_integration_wasp_in_a_box(
    hass: HomeAssistant,
    wasp_in_a_box_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with Wasp in a box (and aggregates) config."""

    await init_integration(hass, [wasp_in_a_box_config_entry])
    yield
    await shutdown_integration(hass, [wasp_in_a_box_config_entry])


# Entities


@pytest.fixture(name="entities_wasp_in_a_box")
async def setup_entities_wasp_in_a_box(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create motion and door sensors."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion_sensor",
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        ),
        MockBinarySensor(
            name="door_sensor",
            unique_id="unique_door",
            device_class=BinarySensorDeviceClass.DOOR,
        ),
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


# Tests


async def test_wasp_in_a_box_logic(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box,
) -> None:
    """Test the Wasp in a box sensor logic."""

    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id

    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    motion_aggregate_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_motion"
    door_aggregate_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{DEFAULT_MOCK_AREA}_aggregate_door"

    # Ensure source entities are loaded
    motion_sensor_state = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_OFF)

    door_sensor_state = hass.states.get(door_sensor_entity_id)
    assert_state(door_sensor_state, STATE_OFF)

    # Ensure aggregates are loaded
    motion_aggregate_state = hass.states.get(motion_aggregate_entity_id)
    assert_state(motion_aggregate_state, STATE_OFF)

    door_aggregate_state = hass.states.get(door_aggregate_entity_id)
    assert_state(door_aggregate_state, STATE_OFF)

    # Ensure Wasp in a box sensor is loaded
    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    # Test motion door open behavior
    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    # Test motion on door closed behavior
    hass.states.async_set(door_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)

    # Test door open releases wasp
    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Wait a bit for wasp sensor to trigger
    await asyncio.sleep(1)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)


async def test_wasp_in_a_box_as_presence(
    hass: HomeAssistant,
    entities_wasp_in_a_box: list[MockBinarySensor],
    _setup_integration_wasp_in_a_box,
) -> None:
    """Test the Wasp in a box sensor triggers area presence."""

    motion_sensor_entity_id = entities_wasp_in_a_box[0].entity_id
    door_sensor_entity_id = entities_wasp_in_a_box[1].entity_id
    wasp_in_a_box_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_wasp_in_a_box_{DEFAULT_MOCK_AREA}"
    )
    area_state_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"

    # Set initial values
    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    hass.states.async_set(door_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Ensure initial values are set
    door_sensor_state = hass.states.get(door_sensor_entity_id)
    assert_state(door_sensor_state, STATE_ON)

    motion_sensor_state = hass.states.get(motion_sensor_entity_id)
    assert_state(motion_sensor_state, STATE_OFF)

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    area_sensor_state = hass.states.get(area_state_entity_id)
    assert_state(area_sensor_state, STATE_OFF)
    assert_in_attribute(
        area_sensor_state, ATTR_PRESENCE_SENSORS, wasp_in_a_box_entity_id
    )

    # Test presence tracking
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_ON)

    area_sensor_state = hass.states.get(area_state_entity_id)
    assert_state(area_sensor_state, STATE_ON)
    assert_in_attribute(area_sensor_state, ATTR_ACTIVE_SENSORS, wasp_in_a_box_entity_id)

    hass.states.async_set(motion_sensor_entity_id, STATE_OFF)
    await hass.async_block_till_done()

    wasp_in_a_box_state = hass.states.get(wasp_in_a_box_entity_id)
    assert_state(wasp_in_a_box_state, STATE_OFF)

    area_sensor_state = hass.states.get(area_state_entity_id)
    assert_state(area_sensor_state, STATE_OFF)
