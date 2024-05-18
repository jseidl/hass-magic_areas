"""Test for integration init."""

import asyncio
import contextlib
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .common import VirtualClock, async_mock_service
from .mocks import MockBinarySensor, MockLight

_LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize(("automated", "state"), [(False, STATE_OFF), (True, STATE_ON)])
async def test_light_on_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: list[str],
    one_motion: list[MockBinarySensor],
    _setup_integration,
    automated: bool,
    state: str,
    event_loop_policy,
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    control_entity = hass.states.get(f"{SWITCH_DOMAIN}.area_light_control_kitchen")
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_kitchen")
    occupied_lights = hass.states.get(f"{LIGHT_DOMAIN}.extended_kitchen")
    extended_lights = hass.states.get(f"{LIGHT_DOMAIN}.occupied_kitchen")

    calls = async_mock_service(hass, LIGHT_DOMAIN, "turn_on")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    assert occupied_lights is not None
    assert extended_lights is not None
    for light in one_light:
        e = hass.states.get(light)
        assert e.state == STATE_OFF
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"
    assert occupied_lights.state == STATE_OFF
    assert extended_lights.state == STATE_OFF

    # Make the sensor on to make the area occupied and setup automated.
    if automated:
        service_data = {
            ATTR_ENTITY_ID: f"{SWITCH_DOMAIN}.area_light_control_kitchen",
        }
        await hass.services.async_call(SWITCH_DOMAIN, SERVICE_TURN_ON, service_data)
    one_motion[0].turn_on()
    await hass.async_block_till_done()

    # Reload the sensors and they should have changed.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_kitchen")
    assert area_binary_sensor.state == "occupied"
    if automated:
        assert len(calls) == 1
        assert calls[0].data == {
            "entity_id": f"{LIGHT_DOMAIN}.occupied_kitchen",
            "brightness": 255,
        }
        assert calls[0].service == SERVICE_TURN_ON
    else:
        assert len(calls) == 0

    # Delay for a while and it should go into extended mode.
    one_motion[0].turn_off()
    await hass.async_block_till_done()
    await asyncio.sleep(5)
    await hass.async_block_till_done()
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_kitchen")
    assert area_binary_sensor.state == STATE_OFF

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
