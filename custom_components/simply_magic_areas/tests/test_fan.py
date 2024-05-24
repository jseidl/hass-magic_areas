"""Test for the fans."""

import asyncio
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.simply_magic_areas.const import DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .common import async_mock_service
from .mocks import MockBinarySensor, MockSensor

_LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize(("automated", "state"), [(False, STATE_OFF), (True, STATE_ON)])
async def test_fan_on_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_fan: list[str],
    one_motion: list[MockBinarySensor],
    _setup_integration,
    automated: bool,
    state: str,
) -> None:
    """Test loading the integration."""
    # Validate the right enties were created.
    control_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_magic_light_control_kitchen"
    )
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_magic_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")

    calls = async_mock_service(hass, FAN_DOMAIN, "turn_on")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    for fan in one_fan:
        e = hass.states.get(fan)
        assert e.state == STATE_OFF
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    # Make the sensor on to make the area occupied and setup automated.
    if automated:
        service_data = {
            ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.area_magic_light_control_kitchen",
        }
        await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)
    one_motion[0].turn_on()
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")
    assert area_binary_sensor.state == "occupied"
    assert len(calls) == 0

    # Delay for a while and it should go into extended mode.
    one_motion[0].turn_off()
    await hass.async_block_till_done()
    await asyncio.sleep(4)
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")
    assert area_binary_sensor.state == "extended"
    if automated:
        assert len(calls) == 1
        assert calls[0].data == {
            "entity_id": f"{FAN_DOMAIN}.simple_magic_areas_fan_kitchen",
        }
        assert calls[0].service == SERVICE_TURN_ON
    else:
        assert len(calls) == 0

    await asyncio.sleep(3)
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")
    assert area_binary_sensor.state == "clear"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    await hass.async_block_till_done()


async def test_fan_on_off_humidity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_fan: list[str],
    one_motion: list[MockBinarySensor],
    one_sensor_humidity: list[MockSensor],
    _setup_integration,
) -> None:
    """Test loading the integration."""
    # Validate the right enties were created.
    control_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_magic_light_control_kitchen"
    )
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_magic_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")

    calls = async_mock_service(hass, FAN_DOMAIN, "turn_on")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    for fan in one_fan:
        e = hass.states.get(fan)
        assert e.state == STATE_OFF
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    # Make the sensor on to make the area occupied and setup automated.
    service_data = {
        ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.area_magic_light_control_kitchen",
    }
    await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)
    hass.states.async_set(one_sensor_humidity[0].entity_id, 10)
    hass.states.async_set(one_sensor_humidity[0].entity_id, 20)
    hass.states.async_set(one_sensor_humidity[0].entity_id, 30)
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")
    area_humidity_occupied = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.simple_magic_areas_humidity_occupancy_kitchen"
    )
    area_humidity_empty = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.simple_magic_areas_humidity_empty_kitchen"
    )
    assert area_humidity_occupied.state == STATE_ON
    assert area_humidity_empty.state == STATE_OFF
    assert area_binary_sensor.state == "clear"
    assert len(calls) == 1
    assert calls[0].data == {
        "entity_id": f"{FAN_DOMAIN}.simple_magic_areas_fan_kitchen",
    }

    # Push events down, should turn on the down trending sensor.
    hass.states.async_set(one_sensor_humidity[0].entity_id, 20)
    hass.states.async_set(one_sensor_humidity[0].entity_id, 30)
    hass.states.async_set(one_sensor_humidity[0].entity_id, 5)
    await hass.async_block_till_done()
    area_humidity_occupied = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.simple_magic_areas_humidity_occupancy_kitchen"
    )
    area_humidity_empty = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.simple_magic_areas_humidity_empty_kitchen"
    )
    assert area_humidity_occupied.state == STATE_ON
    assert area_humidity_empty.state == STATE_ON
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")
    assert area_binary_sensor.state == "clear"
    assert len(calls) == 1

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    await hass.async_block_till_done()
