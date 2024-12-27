"""Test for meta area changes and how the system handles it."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .mocks import MockBinarySensor
from .const import MockAreaIds
from custom_components.magic_areas.const import AreaStates

_LOGGER = logging.getLogger(__name__)


async def test_meta_area_primary_state_change(
    hass: HomeAssistant,
    entities_binary_sensor_motion_all_areas_with_meta: dict[
        MockAreaIds, list[MockBinarySensor]
    ],
    _setup_integration_all_areas_with_meta,
) -> None:
    """Test loading the integration."""

    # Test initialization
    for (
        area_id,
        entity_list,
    ) in entities_binary_sensor_motion_all_areas_with_meta.items():
        assert entity_list is not None
        assert len(entity_list) == 1

        entity_ids = [entity.entity_id for entity in entity_list]

        # Check area sensor is created
        area_sensor_entity_id = (
            f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{area_id}_area_state"
        )
        area_binary_sensor = hass.states.get(area_sensor_entity_id)
        assert area_binary_sensor is not None
        assert area_binary_sensor.state == STATE_OFF
        assert set(entity_ids) == set(area_binary_sensor.attributes["presence_sensors"])
        assert AreaStates.CLEAR in area_binary_sensor.attributes["states"]

    # Toggle interior area and check interior meta area
    kitchen_motion_sensor_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.KITCHEN
    ][0].entity_id
    hass.states.async_set(kitchen_motion_sensor_id, STATE_ON)
    await hass.async_block_till_done()

    kitchen_motion_sensor_state = hass.states.get(kitchen_motion_sensor_id)
    assert kitchen_motion_sensor_state is not None
    assert kitchen_motion_sensor_state.state == STATE_ON

    kitchen_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.KITCHEN.value}_area_state"
    )
    assert kitchen_area_sensor_state is not None
    assert kitchen_area_sensor_state.state == STATE_ON

    interior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.INTERIOR.value}_area_state"
    )
    assert interior_area_sensor_state is not None
    assert interior_area_sensor_state.state == STATE_ON

    exterior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.EXTERIOR.value}_area_state"
    )
    assert exterior_area_sensor_state is not None
    assert exterior_area_sensor_state.state == STATE_OFF

    global_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.GLOBAL.value}_area_state"
    )
    assert global_area_sensor_state is not None
    assert global_area_sensor_state.state == STATE_ON

    hass.states.async_set(kitchen_motion_sensor_id, STATE_OFF)
    await hass.async_block_till_done()

    kitchen_motion_sensor_state = hass.states.get(kitchen_motion_sensor_id)
    assert kitchen_motion_sensor_state is not None
    assert kitchen_motion_sensor_state.state == STATE_OFF

    kitchen_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.KITCHEN.value}_area_state"
    )
    assert kitchen_area_sensor_state is not None
    assert kitchen_area_sensor_state.state == STATE_OFF

    interior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.INTERIOR.value}_area_state"
    )
    assert interior_area_sensor_state is not None
    assert interior_area_sensor_state.state == STATE_OFF

    exterior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.EXTERIOR.value}_area_state"
    )
    assert exterior_area_sensor_state is not None
    assert exterior_area_sensor_state.state == STATE_OFF

    global_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.GLOBAL.value}_area_state"
    )
    assert global_area_sensor_state is not None
    assert global_area_sensor_state.state == STATE_OFF

    # Toggle exterior area
    backyard_motion_sensor_id = entities_binary_sensor_motion_all_areas_with_meta[
        MockAreaIds.BACKYARD
    ][0].entity_id
    hass.states.async_set(backyard_motion_sensor_id, STATE_ON)
    await hass.async_block_till_done()

    backyard_motion_sensor_state = hass.states.get(backyard_motion_sensor_id)
    assert backyard_motion_sensor_state is not None
    assert backyard_motion_sensor_state.state == STATE_ON

    backyard_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.BACKYARD.value}_area_state"
    )
    assert backyard_area_sensor_state is not None
    assert backyard_area_sensor_state.state == STATE_ON

    interior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.INTERIOR.value}_area_state"
    )
    assert interior_area_sensor_state is not None
    assert interior_area_sensor_state.state == STATE_OFF

    exterior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.EXTERIOR.value}_area_state"
    )
    assert exterior_area_sensor_state is not None
    assert exterior_area_sensor_state.state == STATE_ON

    global_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.GLOBAL.value}_area_state"
    )
    assert global_area_sensor_state is not None
    assert global_area_sensor_state.state == STATE_ON

    hass.states.async_set(backyard_motion_sensor_id, STATE_OFF)
    await hass.async_block_till_done()

    backyard_motion_sensor_state = hass.states.get(kitchen_motion_sensor_id)
    assert backyard_motion_sensor_state is not None
    assert backyard_motion_sensor_state.state == STATE_OFF

    backyard_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.BACKYARD.value}_area_state"
    )
    assert backyard_area_sensor_state is not None
    assert backyard_area_sensor_state.state == STATE_OFF

    interior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.INTERIOR.value}_area_state"
    )
    assert interior_area_sensor_state is not None
    assert interior_area_sensor_state.state == STATE_OFF

    exterior_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.EXTERIOR.value}_area_state"
    )
    assert exterior_area_sensor_state is not None
    assert exterior_area_sensor_state.state == STATE_OFF

    global_area_sensor_state = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{MockAreaIds.GLOBAL.value}_area_state"
    )
    assert global_area_sensor_state is not None
    assert global_area_sensor_state.state == STATE_OFF
