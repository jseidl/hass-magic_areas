"""Test for aggregate (group) sensor behavior."""

import logging
import asyncio

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.threshold.binary_sensor import ATTR_UPPER
from homeassistant.const import LIGHT_LUX, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .mocks import MockBinarySensor

_LOGGER = logging.getLogger(__name__)


async def test_threshold_sensor_light(
    hass: HomeAssistant,
    entities_sensor_illuminance_multiple: list[MockBinarySensor],
    _setup_integration_threshold,
) -> None:
    """Test the light from illuminance threshold sensor."""

    threshold_sensor_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_threshold_kitchen_threshold_light"
    )

    aggregate_sensor_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_kitchen_aggregate_illuminance"
    )

    # Ensure aggregate sensor was created
    aggregate_sensor_state = hass.states.get(aggregate_sensor_id)
    assert aggregate_sensor_state is not None
    assert float(aggregate_sensor_state.state) == 0.0

    # Ensure threhsold sensor was created
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert threshold_sensor_state is not None
    assert threshold_sensor_state.state == STATE_OFF

    sensor_threhsold_upper = int(threshold_sensor_state.attributes[ATTR_UPPER])

    # Set illuminance sensor values to double the threhsold upper value
    for mock_entity in entities_sensor_illuminance_multiple:
        hass.states.async_set(
            mock_entity.entity_id,
            sensor_threhsold_upper * 2,
            attributes={"unit_of_measurement": LIGHT_LUX},
        )
    await hass.async_block_till_done()

    # Wait a bit for threshold sensor to trigger
    await asyncio.sleep(5)
    await hass.async_block_till_done()

    # Ensure threhsold sensor is triggered
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert threshold_sensor_state is not None
    assert threshold_sensor_state.state == STATE_ON

    # Reset illuminance sensor values to 0
    for mock_entity in entities_sensor_illuminance_multiple:
        hass.states.async_set(
            mock_entity.entity_id, 0.0, attributes={"unit_of_measurement": LIGHT_LUX}
        )
    await hass.async_block_till_done()

    # Wait a bit for threshold sensor to trigger
    await asyncio.sleep(5)
    await hass.async_block_till_done()

    # Ensure threhsold sensor is cleared
    threshold_sensor_state = hass.states.get(threshold_sensor_id)
    assert threshold_sensor_state is not None
    assert threshold_sensor_state.state == STATE_OFF
