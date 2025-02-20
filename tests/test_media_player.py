"""Test for aggregate (group) sensor behavior."""

from collections.abc import AsyncGenerator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaType,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_MEDIA_STOP,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
)
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    DOMAIN,
    AreaStates,
)

from tests.common import (
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
)
from tests.const import DEFAULT_MOCK_AREA, MockAreaIds
from tests.mocks import MockBinarySensor, MockMediaPlayer

_LOGGER = logging.getLogger(__name__)


# Fixtures


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


# Entities


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


# Tests


async def test_area_aware_media_player(
    hass: HomeAssistant,
    entities_media_player_single: list[MockMediaPlayer],
    entities_binary_sensor_motion_one: list[MockBinarySensor],
    _setup_integration_area_aware_media_player: AsyncGenerator[Any, None],
) -> None:
    """Test the area aware media player."""

    area_aware_media_player_id = (
        f"{MEDIA_PLAYER_DOMAIN}.magic_areas_area_aware_media_player_global"
    )

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )
    motion_sensor_entity_id = entities_binary_sensor_motion_one[0].entity_id

    # Initialization tests

    # Mock media player
    media_player_state = hass.states.get(entities_media_player_single[0].entity_id)
    assert media_player_state is not None
    assert media_player_state.state == STATE_OFF

    # Area-Aware media player
    area_aware_media_player_state = hass.states.get(area_aware_media_player_id)
    assert area_aware_media_player_state is not None
    assert area_aware_media_player_state.state == STATE_IDLE

    # Test area clear

    # Ensure area is clear
    area_state = hass.states.get(area_sensor_entity_id)
    assert area_state is not None
    assert area_state.state == STATE_OFF

    # Send play to AAMP
    service_data = {
        ATTR_ENTITY_ID: area_aware_media_player_id,
        ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
        ATTR_MEDIA_CONTENT_ID: 42,
    }
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, service_data
    )
    await hass.async_block_till_done()

    # Ensure area MP & AAMP is NOT playing
    media_player_state = hass.states.get(entities_media_player_single[0].entity_id)
    assert media_player_state is not None
    assert media_player_state.state == STATE_OFF

    area_aware_media_player_state = hass.states.get(area_aware_media_player_id)
    assert area_aware_media_player_state is not None
    assert area_aware_media_player_state.state == STATE_IDLE

    # Test area occupied

    # Ensure area is occupied
    # Turn on motion sensor
    hass.states.async_set(motion_sensor_entity_id, STATE_ON)
    await hass.async_block_till_done()

    area_binary_sensor = hass.states.get(area_sensor_entity_id)
    motion_sensor = hass.states.get(motion_sensor_entity_id)

    assert motion_sensor is not None
    assert motion_sensor.state == STATE_ON
    assert area_binary_sensor is not None
    assert area_binary_sensor.state == STATE_ON
    assert AreaStates.OCCUPIED in area_binary_sensor.attributes["states"]

    # Send play to AAMP
    service_data = {
        ATTR_ENTITY_ID: area_aware_media_player_id,
        ATTR_MEDIA_CONTENT_TYPE: MediaType.MUSIC,
        ATTR_MEDIA_CONTENT_ID: 42,
    }
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, service_data
    )
    await hass.async_block_till_done()

    # Ensure area MP is playing
    media_player_state = hass.states.get(entities_media_player_single[0].entity_id)
    assert media_player_state is not None
    assert media_player_state.state == STATE_PLAYING

    area_aware_media_player_state = hass.states.get(area_aware_media_player_id)
    assert area_aware_media_player_state is not None
    assert area_aware_media_player_state.state == STATE_IDLE

    # Turn off area MP
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_MEDIA_STOP,
        {ATTR_ENTITY_ID: entities_media_player_single[0].entity_id},
    )
    await hass.async_block_till_done()

    # Ensure area MP is stopped
    media_player_state = hass.states.get(entities_media_player_single[0].entity_id)
    assert media_player_state is not None
    assert media_player_state.state == STATE_IDLE

    # Test area occupied + sleep

    # Ensure area is occupied + sleep

    # Send play to AAMP

    # Ensure area MP is NOT playing

    # Turn off AAMP
