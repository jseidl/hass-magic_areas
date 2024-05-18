"""Fixtures for tests."""

from collections.abc import Generator
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import (
    CONF_ID,
    CONF_NAME,
    CONF_ON_STATES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    CONF_CLEAR_TIMEOUT,
)
from homeassistant.components import light
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.light import (
    ATTR_SUPPORTED_COLOR_MODES,
    DOMAIN as LIGHT_DOMAIN,
    ColorMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    CONF_PLATFORM,
    STATE_OFF,
    STATE_ON,
    Platform,
    SERVICE_TURN_OFF,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.setup import async_setup_component

from .common import setup_test_component_platform
from .mocks import MockBinarySensor, MockLight

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
    data = {
        CONF_NAME: AREA_NAME,
        CONF_ID: AREA_NAME,
        CONF_UPDATE_INTERVAL: 60,
        CONF_PRESENCE_SENSOR_DEVICE_CLASS: [BinarySensorDeviceClass.MOTION],
        CONF_ON_STATES: [STATE_ON],
        CONF_CLEAR_TIMEOUT: 3,
    }
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="one_motion")
async def setup_one_sensor(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create one mock sensor and setup the system with ti."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion sensor",
            is_on=True,
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        )
    ]
    setup_test_component_platform(
        hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities
    )
    assert await async_setup_component(
        hass, BINARY_SENSOR_DOMAIN, {BINARY_SENSOR_DOMAIN: {CONF_PLATFORM: "test"}}
    )
    await hass.async_block_till_done()
    entity_registry = async_get_er(hass)
    entity_registry.async_update_entity(
        "binary_sensor.motion_sensor",
        area_id=AREA_NAME,
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="one_light")
async def setup_one_light(hass: HomeAssistant) -> list[str]:
    """Create one mock light and setup the system with ti."""
    # mock_light_sensor_entities = [
    #     MockLight("light_1", STATE_OFF, unique_id="lightfrog")
    # ]
    # setup_test_component_platform(hass, LIGHT_DOMAIN, mock_light_sensor_entities)
    # assert await async_setup_component(
    #     hass, LIGHT_DOMAIN, {LIGHT_DOMAIN: {CONF_PLATFORM: "test"}}
    # )
    # await hass.async_block_till_done()
    # entity_registry = async_get_er(hass)
    # await hass.services.async_call(
    #     LIGHT_DOMAIN,
    #     SERVICE_TURN_OFF,
    #     {"entity_id": mock_light_sensor_entities[0].entity_id},
    #     blocking=True,
    # )
    # await hass.async_block_till_done()
    # await entity_registry.async_update_entity(
    #     mock_light_sensor_entities[0].entity_id,
    #     area_id=AREA_NAME,
    # )
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
    hass.states.async_set(
        "light.test_5678", "off", {ATTR_SUPPORTED_COLOR_MODES: [ColorMode.HS]}
    )
    return ["light.test_5678"]


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
