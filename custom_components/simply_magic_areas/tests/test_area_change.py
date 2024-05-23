"""Test for integration init."""

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.simply_magic_areas.const import DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
    RegistryEntry,
    async_get as async_get_er,
)
from homeassistant.helpers.area_registry import async_get as async_get_ar

from .mocks import MockBinarySensor, MockLight

_LOGGER = logging.getLogger(__name__)


async def test_area_change(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    one_light: list[str],
    one_motion: list[MockBinarySensor],
    _setup_integration,
) -> None:
    """Test loading the integration."""
    assert config_entry.state is ConfigEntryState.LOADED

    registry = async_get_ar(hass)
    registry.async_get_or_create("frog")

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(f"{SELECT_DOMAIN}.area_magic_kitchen")

    assert area_binary_sensor is not None
    assert area_binary_sensor.state == "clear"
    await hass.async_block_till_done()

    entity_registry = async_get_er(hass)
    entity_registry.async_update_entity(
        one_light[0],
        area_id="frog",
    )
    await hass.async_block_till_done()

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
