"""Test for integration init."""

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from .mocks import MockLight

_LOGGER = logging.getLogger(__name__)


async def test_init_no_devices(
    hass: HomeAssistant, config_entry: MockConfigEntry, _setup_integration
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    control_entity = hass.states.get(f"{SWITCH_DOMAIN}.area_light_control_kitchen")
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{DOMAIN}.area_kitchen")
    occupied_lights = hass.states.get(f"{LIGHT_DOMAIN}.extended_kitchen")
    extended_lights = hass.states.get(f"{LIGHT_DOMAIN}.occupied_kitchen")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    assert occupied_lights is None
    assert extended_lights is None
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_init_with_lights(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: MockLight,
    _setup_integration,
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    control_entity = hass.states.get(f"{SWITCH_DOMAIN}.area_light_control_kitchen")
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{DOMAIN}.area_kitchen")
    occupied_lights = hass.states.get(f"{LIGHT_DOMAIN}.extended_kitchen")
    extended_lights = hass.states.get(f"{LIGHT_DOMAIN}.occupied_kitchen")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    assert occupied_lights is not None
    assert extended_lights is not None
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_init_with_lights_and_sensor(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: str,
    one_motion: str,
    _setup_integration,
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    # Validate the right enties were created.
    control_entity = hass.states.get(f"{SWITCH_DOMAIN}.area_light_control_kitchen")
    manual_override_entity = hass.states.get(
        f"{SWITCH_DOMAIN}.area_manual_override_active_kitchen"
    )
    area_binary_sensor = hass.states.get(f"{BINARY_SENSOR_DOMAIN}.area_kitchen")
    occupied_lights = hass.states.get(f"{LIGHT_DOMAIN}.extended_kitchen")
    extended_lights = hass.states.get(f"{LIGHT_DOMAIN}.occupied_kitchen")

    assert control_entity is not None
    assert manual_override_entity is not None
    assert area_binary_sensor is not None
    assert occupied_lights is not None
    assert extended_lights is not None
    assert control_entity.state == STATE_OFF
    assert manual_override_entity.state == STATE_OFF
    assert area_binary_sensor.state == "clear"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
