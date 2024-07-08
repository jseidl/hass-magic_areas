"""Fixtures for tests."""

from collections.abc import AsyncGenerator, Generator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from random import randint

from custom_components.magic_areas.const import (
    CONF_ACCENT_ENTITY,
    CONF_CLEAR_TIMEOUT,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_FEATURE_AGGREGATION,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_NAME,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
    DOMAIN,
    AreaType,
)
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_PLATFORM, UnitOfTemperature, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.setup import async_setup_component

from .common import setup_test_component_platform
from .mocks import MockBinarySensor, MockSensor

AREA_NAME = "kitchen"
_LOGGER = logging.getLogger(__name__)

BASIC_CONFIG_ENTRY_DATA = {
    CONF_NAME: AREA_NAME,
    CONF_ID: AREA_NAME,
    CONF_CLEAR_TIMEOUT: 0,  # @FIXME change this back to 1 once i fix the timeout waiting thing
    CONF_UPDATE_INTERVAL: 60,
    CONF_EXTENDED_TIMEOUT: 5,
    CONF_TYPE: AreaType.INTERIOR,
    CONF_EXCLUDE_ENTITIES: [],
    CONF_INCLUDE_ENTITIES: [],
    CONF_PRESENCE_SENSOR_DEVICE_CLASS: DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
    CONF_ENABLED_FEATURES: {},
}

# Helpers


async def init_integration(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Set up the integration."""
    registry = async_get_ar(hass)
    registry.async_get_or_create(AREA_NAME)

    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED


async def shutdown_integration(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Teardown the integration."""

    _LOGGER.info("Unloading integration.")
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
    _LOGGER.info("Integration unloaded.")


async def setup_mock_entities(
    hass: HomeAssistant, domain: str, entities: list[Any]
) -> None:
    """Set up multiple mock entities at once."""

    setup_test_component_platform(hass, domain, entities)
    assert await async_setup_component(hass, domain, {domain: {CONF_PLATFORM: "test"}})
    await hass.async_block_till_done()
    entity_registry = async_get_er(hass)
    for mock_sensor in entities:
        entity_registry.async_update_entity(
            mock_sensor.entity_id,
            area_id=AREA_NAME,
        )
    await hass.async_block_till_done()


# Fixtures


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None, None, None]:
    """Enable custom integration."""
    _ = enable_custom_integrations  # unused
    yield

# Config entries

@pytest.fixture(name="config_entry")
def mock_config_entry() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = dict(BASIC_CONFIG_ENTRY_DATA)
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="secondary_states_config_entry")
def mock_config_entry_secondary_states() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = dict(BASIC_CONFIG_ENTRY_DATA)
    data.update(
        {
            CONF_SECONDARY_STATES: {
                CONF_ACCENT_ENTITY: "binary_sensor.accent_sensor",
                CONF_DARK_ENTITY: "binary_sensor.area_light_sensor",
                CONF_SLEEP_ENTITY: "binary_sensor.sleep_sensor",
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)

@pytest.fixture(name="aggregates_config_entry")
def mock_config_entry_aggregates() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = dict(BASIC_CONFIG_ENTRY_DATA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_AGGREGATION: {
                    CONF_AGGREGATES_MIN_ENTITIES: 1
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)

# Entities

@pytest.fixture(name="secondary_states_sensors")
async def setup_secondary_state_sensors(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create binary sensors for the secondary states."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="sleep_sensor",
            unique_id="sleep_sensor",
            device_class=None,
        ),
        MockBinarySensor(
            name="area_light_sensor",
            unique_id="area_light_sensor",
            device_class=BinarySensorDeviceClass.LIGHT,
        ),
        MockBinarySensor(
            name="accent_sensor",
            unique_id="accent_sensor",
            device_class=None,
        ),
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_motion_one")
async def setup_entities_binary_sensor_motion_one(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create one mock sensor and setup the system with it."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion_sensor",
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        )
    ]
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)
    return mock_binary_sensor_entities

@pytest.fixture(name="entities_binary_sensor_motion_multiple")
async def setup_entities_binary_sensor_motion_multiple(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_binary_sensor_entities = []
    for i in range(nr_entities):
        mock_binary_sensor_entities.append(
            MockBinarySensor(
                name=f"motion_sensor_{i}",
                unique_id=f"motion_sensor_{i}",
                device_class=BinarySensorDeviceClass.MOTION
            )
        )
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)
    return mock_binary_sensor_entities

@pytest.fixture(name="entities_binary_sensor_connectivity_multiple")
async def setup_entities_binary_sensor_connectivity_multiple(hass: HomeAssistant) -> list[MockBinarySensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_binary_sensor_entities = []
    for i in range(nr_entities):
        mock_binary_sensor_entities.append(
            MockBinarySensor(
                name=f"connectivity_sensor_{i}",
                unique_id=f"connectivity_sensor_{i}",
                device_class=BinarySensorDeviceClass.CONNECTIVITY
            )
        )
    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)
    return mock_binary_sensor_entities

@pytest.fixture(name="entities_sensor_temperature_multiple")
async def setup_entities_sensor_temperature_multiple(hass: HomeAssistant) -> list[MockSensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_sensor_entities = []
    for i in range(nr_entities):
        random_value = randint(0, 100)
        mock_sensor_entities.append(
            MockSensor(
                name=f"temperature_sensor_{i}",
                unique_id=f"temperature_sensor_{i}",
                native_value=random_value,
                device_class=SensorDeviceClass.TEMPERATURE,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                unit_of_measurement=UnitOfTemperature.CELSIUS,
                extra_state_attributes={
                    "unit_of_measurement": UnitOfTemperature.CELSIUS,
                },
            )
        )
    await setup_mock_entities(hass, SENSOR_DOMAIN, mock_sensor_entities)
    return mock_sensor_entities

@pytest.fixture(name="entities_sensor_current_multiple")
async def setup_entities_sensor_current_multiple(hass: HomeAssistant) -> list[MockSensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_sensor_entities = []
    for i in range(nr_entities):
        random_value = randint(0, 100)
        mock_sensor_entities.append(
            MockSensor(
                name=f"current_sensor_{i}",
                unique_id=f"current_sensor_{i}",
                native_value=random_value,
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                extra_state_attributes={
                    "unit_of_measurement": UnitOfElectricCurrent.AMPERE,
                },
            )
        )
    await setup_mock_entities(hass, SENSOR_DOMAIN, mock_sensor_entities)
    return mock_sensor_entities

# Integration set-ups

@pytest.fixture(name="_setup_integration")
async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with basic config."""

    await init_integration(hass, config_entry)
    yield
    await shutdown_integration(hass, config_entry)


@pytest.fixture(name="_setup_integration_secondary_states")
async def setup_integration_secondary_states(
    hass: HomeAssistant,
    secondary_states_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, secondary_states_config_entry)
    yield
    await shutdown_integration(hass, secondary_states_config_entry)

@pytest.fixture(name="_setup_integration_aggregates")
async def setup_integration_aggregates(
    hass: HomeAssistant,
    aggregates_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, aggregates_config_entry)
    yield
    await shutdown_integration(hass, aggregates_config_entry)
