"""Fixtures for tests."""

from collections.abc import AsyncGenerator, Generator
import logging
from random import randint
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.cover.const import DOMAIN as COVER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor.const import (
    DOMAIN as SENSOR_DOMAIN,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_FLOOR_ID,
    CONF_PLATFORM,
    LIGHT_LUX,
    STATE_OFF,
    UnitOfElectricCurrent,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.floor_registry import async_get as async_get_fr
from homeassistant.setup import async_setup_component

from .common import get_basic_config_entry_data, setup_test_component_platform
from .const import DEFAULT_MOCK_AREA, MOCK_AREAS, MockAreaIds
from .mocks import MockBinarySensor, MockCover, MockLight, MockMediaPlayer, MockSensor
from custom_components.magic_areas.const import (
    CONF_ACCENT_ENTITY,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_COVER_GROUPS,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_KEEP_ONLY_ENTITIES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_OVERHEAD_LIGHTS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    CONF_TYPE,
    DOMAIN,
    AreaStates,
    AreaType,
)

_LOGGER = logging.getLogger(__name__)

# Helpers


async def init_integration(
    hass: HomeAssistant,
    config_entries: list[MockConfigEntry],
    areas: list[MockAreaIds] | None = None,
) -> None:
    """Set up the integration."""

    if not areas:
        areas = [DEFAULT_MOCK_AREA]

    area_registry = async_get_ar(hass)
    floor_registry = async_get_fr(hass)

    # Register areas
    for area in areas:
        area_object = MOCK_AREAS[area]
        floor_id: str | None = None

        if area_object[ATTR_FLOOR_ID]:
            assert area_object[ATTR_FLOOR_ID] is not None
            floor_name = str(area_object[ATTR_FLOOR_ID])
            floor_entry = floor_registry.async_get_floor_by_name(floor_name)
            if not floor_entry:
                floor_entry = floor_registry.async_create(floor_name)
            assert floor_entry is not None
            floor_id = floor_entry.floor_id
        area_registry.async_create(name=area.value, floor_id=floor_id)

    for config_entry in config_entries:
        config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    for config_entry in config_entries:
        assert config_entry.state is ConfigEntryState.LOADED


async def shutdown_integration(
    hass: HomeAssistant, config_entries: list[MockConfigEntry]
) -> None:
    """Teardown the integration."""

    _LOGGER.info("Unloading integration.")
    for config_entry in config_entries:
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)

    for config_entry in config_entries:
        assert config_entry.state is ConfigEntryState.NOT_LOADED
    _LOGGER.info("Integration unloaded.")


async def setup_mock_entities(
    hass: HomeAssistant, domain: str, area_entity_map: dict[MockAreaIds, list[Any]]
) -> None:
    """Set up multiple mock entities at once."""

    all_entities: list[Any] = []
    entity_area_map: dict[Any, MockAreaIds] = {}

    for area_id, entity_list in area_entity_map.items():
        for entity in entity_list:
            all_entities.append(entity)
            entity_area_map[entity.unique_id] = area_id

    # Setup entities
    setup_test_component_platform(hass, domain, all_entities)
    assert await async_setup_component(hass, domain, {domain: {CONF_PLATFORM: "test"}})
    await hass.async_block_till_done()

    # Update area IDs
    entity_registry = async_get_er(hass)
    for entity in all_entities:
        assert entity is not None
        assert entity.entity_id is not None
        assert entity.unique_id is not None
        entity_registry.async_update_entity(
            entity.entity_id,
            area_id=entity_area_map[entity.unique_id].value,
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
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="secondary_states_config_entry")
def mock_config_entry_secondary_states() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
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


@pytest.fixture(name="keep_only_sensor_config_entry")
def mock_config_entry_keep_only_sensor() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_KEEP_ONLY_ENTITIES: ["binary_sensor.motion_sensor_1"]})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="aggregates_config_entry")
def mock_config_entry_aggregates() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_AGGREGATION: {CONF_AGGREGATES_MIN_ENTITIES: 1}
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="threshold_config_entry")
def mock_config_entry_threshold() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_AGGREGATION: {
                    CONF_AGGREGATES_MIN_ENTITIES: 1,
                    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: 600,
                    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD_HYSTERESIS: 10,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="cover_groups_config_entry")
def mock_config_entry_cover_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_ENABLED_FEATURES: {CONF_FEATURE_COVER_GROUPS: {}}})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="basic_light_group_config_entry")
def mock_config_entry_light_group_basic() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_LIGHT_GROUPS: {
                    CONF_OVERHEAD_LIGHTS: [
                        "lihgt.mock_light_1",
                        "lihgt.mock_light_2",
                        "lihgt.mock_light_3",
                    ]
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="area_aware_media_player_global_config_entry")
def mock_config_entry_area_aware_media_player_global() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(MockAreaIds.GLOBAL)
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="area_aware_media_player_area_config_entry")
def mock_config_entry_area_aware_media_player_area() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: {
                    CONF_NOTIFICATION_DEVICES: ["media_player.media_player_1"],
                    CONF_NOTIFY_STATES: [AreaStates.OCCUPIED],
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="ble_tracker_config_entry")
def mock_config_entry_ble_tracker() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_BLE_TRACKERS: {
                    CONF_BLE_TRACKER_ENTITIES: ["sensor.ble_tracker_1"],
                }
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="all_areas_with_meta_config_entry")
def mock_config_entry_all_areas_with_meta_config_entry() -> list[MockConfigEntry]:
    """Fixture for mock configuration entry."""

    config_entries: list[MockConfigEntry] = []
    for area_entry in MockAreaIds:
        data = get_basic_config_entry_data(area_entry)
        data.update(
            {
                CONF_ENABLED_FEATURES: {
                    CONF_FEATURE_AGGREGATION: {CONF_AGGREGATES_MIN_ENTITIES: 1}
                }
            }
        )
        config_entries.append(MockConfigEntry(domain=DOMAIN, data=data))

    return config_entries


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
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_motion_one")
async def setup_entities_binary_sensor_motion_one(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create one mock sensor and setup the system with it."""
    mock_binary_sensor_entities = [
        MockBinarySensor(
            name="motion_sensor",
            unique_id="unique_motion",
            device_class=BinarySensorDeviceClass.MOTION,
        )
    ]
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_motion_multiple")
async def setup_entities_binary_sensor_motion_multiple(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_binary_sensor_entities = []
    for i in range(nr_entities):
        mock_binary_sensor_entities.append(
            MockBinarySensor(
                name=f"motion_sensor_{i}",
                unique_id=f"motion_sensor_{i}",
                device_class=BinarySensorDeviceClass.MOTION,
            )
        )
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_binary_sensor_connectivity_multiple")
async def setup_entities_binary_sensor_connectivity_multiple(
    hass: HomeAssistant,
) -> list[MockBinarySensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_binary_sensor_entities = []
    for i in range(nr_entities):
        mock_binary_sensor_entities.append(
            MockBinarySensor(
                name=f"connectivity_sensor_{i}",
                unique_id=f"connectivity_sensor_{i}",
                device_class=BinarySensorDeviceClass.CONNECTIVITY,
            )
        )
    await setup_mock_entities(
        hass, BINARY_SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_binary_sensor_entities}
    )
    return mock_binary_sensor_entities


@pytest.fixture(name="entities_sensor_temperature_multiple")
async def setup_entities_sensor_temperature_multiple(
    hass: HomeAssistant,
) -> list[MockSensor]:
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
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_sensor_entities}
    )
    return mock_sensor_entities


@pytest.fixture(name="entities_sensor_current_multiple")
async def setup_entities_sensor_current_multiple(
    hass: HomeAssistant,
) -> list[MockSensor]:
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
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_sensor_entities}
    )
    return mock_sensor_entities


@pytest.fixture(name="entities_sensor_illuminance_multiple")
async def setup_entities_sensor_illuminance_multiple(
    hass: HomeAssistant,
) -> list[MockSensor]:
    """Create multiple mock sensor and setup the system with it."""
    nr_entities = 3
    mock_sensor_entities = []
    for i in range(nr_entities):
        mock_sensor_entities.append(
            MockSensor(
                name=f"illuminance_sensor_{i}",
                unique_id=f"illuminance_sensor_{i}",
                native_value=0.0,
                device_class=SensorDeviceClass.ILLUMINANCE,
                native_unit_of_measurement=LIGHT_LUX,
                unit_of_measurement=LIGHT_LUX,
                extra_state_attributes={
                    "unit_of_measurement": LIGHT_LUX,
                },
            )
        )
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_sensor_entities}
    )
    return mock_sensor_entities


@pytest.fixture(name="entities_sensor_cover_all_classes_multiple")
async def setup_entities_sensor_cover_all_classes_multiple(
    hass: HomeAssistant,
) -> list[MockCover]:
    """Create multiple mock sensor and setup the system with it."""

    nr_entities = 3
    mock_cover_entities = []

    for dc in CoverDeviceClass:
        for i in range(nr_entities):
            mock_cover_entities.append(
                MockCover(
                    name=f"cover_{dc.value}_{i}",
                    unique_id=f"cover_{dc.value}_{i}",
                    device_class=dc.value,
                )
            )
    await setup_mock_entities(
        hass, COVER_DOMAIN, {DEFAULT_MOCK_AREA: mock_cover_entities}
    )
    return mock_cover_entities


@pytest.fixture(name="entities_light_many")
async def setup_entities_light_many(
    hass: HomeAssistant,
) -> list[MockLight]:
    """Create multiple mock sensor and setup the system with it."""

    nr_entities = 3
    mock_light_entities = []

    for i in range(nr_entities):
        mock_light_entities.append(
            MockLight(name=f"light_{i}", unique_id=f"light_{i}", state=STATE_OFF)
        )
    await setup_mock_entities(
        hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: mock_light_entities}
    )
    return mock_light_entities


@pytest.fixture(name="entities_media_player_single")
async def setup_entities_media_player_single(
    hass: HomeAssistant,
) -> list[MockMediaPlayer]:
    """Create multiple mock sensor and setup the system with it."""

    mock_media_player_entities = []

    mock_media_player_entities.append(
        MockMediaPlayer(name="media_player_1", unique_id="media_player_1")
    )
    await setup_mock_entities(
        hass, MEDIA_PLAYER_DOMAIN, {DEFAULT_MOCK_AREA: mock_media_player_entities}
    )
    return mock_media_player_entities


@pytest.fixture(name="entities_binary_sensor_motion_all_areas_with_meta")
async def setup_entities_binary_sensor_motion_all_areas_with_meta(
    hass: HomeAssistant,
) -> dict[MockAreaIds, list[MockBinarySensor]]:
    """Create multiple mock sensor and setup the system with it."""

    mock_binary_sensor_entities: dict[MockAreaIds, list[MockBinarySensor]] = {}

    for area in MockAreaIds:
        assert area is not None
        area_object = MOCK_AREAS[area]
        assert area_object is not None
        if area_object[CONF_TYPE] == AreaType.META:
            continue

        mock_sensor = MockBinarySensor(
            name=f"motion_sensor_{area.value}",
            unique_id=f"motion_sensor_{area.value}",
            device_class=BinarySensorDeviceClass.MOTION,
        )

        mock_binary_sensor_entities[area] = [
            mock_sensor,
        ]

    await setup_mock_entities(hass, BINARY_SENSOR_DOMAIN, mock_binary_sensor_entities)

    return mock_binary_sensor_entities


@pytest.fixture(name="entities_ble_sensor_one")
async def setup_entities_ble_sensor_one(
    hass: HomeAssistant,
) -> list[MockSensor]:
    """Create one mock sensor and setup the system with it."""
    mock_ble_sensor_entities = [
        MockSensor(
            name="ble_sensor_1",
            unique_id="unique_ble_sensor",
            device_class=None,
        )
    ]
    await setup_mock_entities(
        hass, SENSOR_DOMAIN, {DEFAULT_MOCK_AREA: mock_ble_sensor_entities}
    )
    return mock_ble_sensor_entities


# Integration set-ups


@pytest.fixture(name="_setup_integration")
async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with basic config."""

    await init_integration(hass, [config_entry])
    yield
    await shutdown_integration(hass, [config_entry])


@pytest.fixture(name="_setup_integration_secondary_states")
async def setup_integration_secondary_states(
    hass: HomeAssistant,
    secondary_states_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [secondary_states_config_entry])
    yield
    await shutdown_integration(hass, [secondary_states_config_entry])


@pytest.fixture(name="_setup_integration_keep_only_sensor")
async def setup_integration_keep_only_sensor(
    hass: HomeAssistant,
    keep_only_sensor_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [keep_only_sensor_config_entry])
    yield
    await shutdown_integration(hass, [keep_only_sensor_config_entry])


@pytest.fixture(name="_setup_integration_aggregates")
async def setup_integration_aggregates(
    hass: HomeAssistant,
    aggregates_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [aggregates_config_entry])
    yield
    await shutdown_integration(hass, [aggregates_config_entry])


@pytest.fixture(name="_setup_integration_threshold")
async def setup_integration_threshold(
    hass: HomeAssistant,
    threshold_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [threshold_config_entry])
    yield
    await shutdown_integration(hass, [threshold_config_entry])


@pytest.fixture(name="_setup_integration_cover_group")
async def setup_integration_cover_group(
    hass: HomeAssistant,
    cover_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [cover_groups_config_entry])
    yield
    await shutdown_integration(hass, [cover_groups_config_entry])


@pytest.fixture(name="_setup_integration_light_group_basic")
async def setup_integration_light_basic(
    hass: HomeAssistant,
    basic_light_group_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(hass, [basic_light_group_config_entry])
    yield
    await shutdown_integration(hass, [basic_light_group_config_entry])


@pytest.fixture(name="_setup_integration_area_aware_media_player")
async def setup_integration_area_aware_media_player(
    hass: HomeAssistant,
    area_aware_media_player_global_config_entry: MockConfigEntry,
    area_aware_media_player_area_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with secondary states config."""

    await init_integration(
        hass,
        [
            area_aware_media_player_area_config_entry,
            area_aware_media_player_global_config_entry,
        ],
    )
    yield
    await shutdown_integration(
        hass,
        [
            area_aware_media_player_area_config_entry,
            area_aware_media_player_global_config_entry,
        ],
    )


@pytest.fixture(name="_setup_integration_ble_tracker")
async def setup_integration_ble_tracker(
    hass: HomeAssistant,
    ble_tracker_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with BLE tracker config."""

    await init_integration(hass, [ble_tracker_config_entry])
    yield
    await shutdown_integration(hass, [ble_tracker_config_entry])


@pytest.fixture(name="_setup_integration_all_areas_with_meta")
async def setup_integration_all_areas_with_meta(
    hass: HomeAssistant,
    all_areas_with_meta_config_entry: list[MockConfigEntry],
) -> AsyncGenerator[Any]:
    """Set up integration with all areas and meta-areas."""

    non_meta_areas: list[MockAreaIds] = []

    for area in MockAreaIds:
        area_object = MOCK_AREAS[area]
        assert area_object is not None
        if area_object[CONF_TYPE] == AreaType.META:
            continue
        non_meta_areas.append(area)

    assert len(non_meta_areas) > 0

    await init_integration(
        hass,
        all_areas_with_meta_config_entry,
        areas=non_meta_areas,
    )
    yield
    await shutdown_integration(
        hass,
        all_areas_with_meta_config_entry,
    )
