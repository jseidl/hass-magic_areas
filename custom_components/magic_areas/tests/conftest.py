"""Fixtures for tests."""

from collections.abc import Generator
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import (
    CONF_ID,
    CONF_NAME,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant.components import light
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.setup import async_setup_component


AREA_NAME = "kitchen"
_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integration."""
    _ = enable_custom_integrations  # unused
    yield


@pytest.fixture(name="config_entry")
def mock_config_entry() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = {CONF_NAME: AREA_NAME, CONF_ID: AREA_NAME, CONF_UPDATE_INTERVAL: 60}
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="one_motion")
def setup_one_sensor(hass: HomeAssistant) -> str:
    """Create one mock sensor and setup the system with ti."""
    entity_registry = async_get_er(hass)
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        "test",
        "1",
    )
    entity_registry.async_update_entity(
        "light.test_5678",
        area_id=AREA_NAME,
    )
    _LOGGER.info("Entities: %s", entity_registry.entities)
    return "light.test_5678"


@pytest.fixture(name="one_light")
def setup_one_light(hass: HomeAssistant) -> str:
    """Create one mock light and setup the system with ti."""
    entity_registry = async_get_er(hass)
    entity_registry.async_get_or_create(
        LIGHT_DOMAIN,
        "test",
        "5678",
    )
    entity_registry.async_update_entity(
        "light.test_5678",
        area_id=AREA_NAME,
    )
    _LOGGER.info("Entities: %s", entity_registry.entities)
    return "light.test_5678"


@pytest.fixture(name="two_lights")
def setup_two_lights(hass: HomeAssistant) -> list[str]:
    """Mock a test component platform for tests."""
    entity_registry = async_get_er(hass)
    entity_registry.async_get_or_create(
        LIGHT_DOMAIN,
        "test",
        "5678",
    )
    entity_registry.async_get_or_create(
        LIGHT_DOMAIN,
        "test",
        "5679",
    )
    entity_registry.async_update_entity(
        "light.test_5678",
        area_id=AREA_NAME,
    )
    entity_registry.async_update_entity(
        "light.test_5679",
        area_id=AREA_NAME,
    )
    _LOGGER.info("Entities: %s", entity_registry.entities)

    return ["light.test_5678", "light.test_5679"]


@pytest.fixture(name="_setup_integration")
async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Set up the integration."""
    registry = async_get_ar(hass)
    registry.async_get_or_create(AREA_NAME)

    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
