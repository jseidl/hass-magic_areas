"""Test for handling lights in the various modes."""

import asyncio
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    LIGHT_LUX,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from ..const import DOMAIN
from .common import async_mock_service
from .mocks import MockBinarySensor, MockSensor

_LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize(("automated", "state"), [(False, STATE_OFF), (True, STATE_ON)])
async def test_light_on_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: list[str],
    one_motion: list[MockBinarySensor],
    _setup_integration,
    automated: bool,
    state: str,
) -> None:
    """Test loading the integration."""
    # Validate the right enties were created.
    control_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.simply_magic_areas_light_control_kitchen"
    )
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.simply_magic_areas_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")

    calls = async_mock_service(hass, LIGHT_DOMAIN, "turn_on")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    for light in one_light:
        e = hass.states.get(light)
        assert e.state == STATE_OFF
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    # Make the sensor on to make the area occupied and setup automated.
    if automated:
        service_data = {
            ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.simply_magic_areas_light_control_kitchen",
        }
        await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)
    one_motion[0].turn_on()
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "occupied"
    if automated:
        assert len(calls) == 1
        assert calls[0].data == {
            "entity_id": f"{LIGHT_DOMAIN}.simply_magic_areas_light_kitchen",
            "brightness": 255,
        }
        assert calls[0].service == SERVICE_TURN_ON
    else:
        assert len(calls) == 0

    # Delay for a while and it should go into extended mode.
    one_motion[0].turn_off()
    await hass.async_block_till_done()
    await asyncio.sleep(4)
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "extended"
    await asyncio.sleep(3)
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "clear"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    await hass.async_block_till_done()


async def test_light_entity_change(
    hass: HomeAssistant,
    config_entry_entities: MockConfigEntry,
    one_light: list[str],
    one_motion: list[MockBinarySensor],
    _setup_integration_entities,
) -> None:
    """Test loading the integration."""
    assert config_entry_entities.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    service_data = {
        ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.simply_magic_areas_light_control_kitchen",
    }
    await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)

    calls = async_mock_service(hass, LIGHT_DOMAIN, "turn_on")
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    one_motion[0].turn_on()
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "occupied"
    assert len(calls) == 1
    assert calls[0].data == {
        "entity_id": f"{LIGHT_DOMAIN}.simply_magic_areas_light_kitchen",
        "brightness": 255,
    }
    assert calls[0].service == SERVICE_TURN_ON
    await hass.async_block_till_done()

    # Set the sleep entity on.
    one_motion[1].turn_on()
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "sleep"

    # Set the bright entity on.
    one_motion[1].turn_off()
    one_motion[2].turn_on()
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "bright"

    # Set the bright entity on.
    one_motion[2].turn_off()
    one_motion[3].turn_on()
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "accented"

    await hass.config_entries.async_unload(config_entry_entities.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry_entities.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("luminesnce", "brightness"), [(0.0, 255), (200.0, 0), (175.0, 63), (300.0, 0)]
)
async def test_light_on_off_with_light_sensor(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: list[str],
    one_motion: list[MockBinarySensor],
    one_sensor_light: list[MockSensor],
    _setup_integration,
    luminesnce: float,
    brightness: int,
) -> None:
    """Test loading the integration."""
    # Validate the right enties were created.
    control_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.simply_magic_areas_light_control_kitchen"
    )
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.simply_magic_areas_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    light_sensor = hass.states.get(
        f"{SENSOR_DOMAIN}.simply_magic_areas_illuminance_kitchen"
    )

    calls = async_mock_service(hass, LIGHT_DOMAIN, "turn_on")
    off_calls = async_mock_service(hass, LIGHT_DOMAIN, "turn_off")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    assert light_sensor is not None
    for light in one_light:
        e = hass.states.get(light)
        assert e.state == STATE_OFF
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    # Make the sensor on to make the area occupied and setup automated, leave the light low to get the brightness correct.
    service_data = {
        ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.simply_magic_areas_light_control_kitchen",
    }
    await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)
    one_motion[0].turn_on()
    hass.states.async_set(
        one_sensor_light[0].entity_id, luminesnce, {"unit_of_measurement": LIGHT_LUX}
    )
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.simply_magic_areas_kitchen")
    assert area_binary_sensor.state == "occupied"
    assert len(off_calls) == 0
    if brightness != 0:
        assert len(calls) == 1
        assert calls[0].data == {
            "entity_id": f"{LIGHT_DOMAIN}.simply_magic_areas_light_kitchen",
            "brightness": brightness,
        }
        assert calls[0].service == SERVICE_TURN_ON

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    await hass.async_block_till_done()
