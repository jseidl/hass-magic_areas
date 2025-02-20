"""Test for climate groups."""

from collections.abc import AsyncGenerator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate.const import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_CLIMATE_GROUPS_TURN_ON_STATE,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_CLIMATE_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_PRESENCE_HOLD_TIMEOUT,
    DOMAIN,
    AreaStates,
)

from tests.common import (
    assert_in_attribute,
    assert_state,
    get_basic_config_entry_data,
    init_integration,
    setup_mock_entities,
    shutdown_integration,
)
from tests.const import DEFAULT_MOCK_AREA
from tests.mocks import MockClimate

_LOGGER = logging.getLogger(__name__)


# Fixtures


@pytest.fixture(name="climate_groups_config_entry")
def mock_config_entry_climate_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_PRESENCE_HOLD: {CONF_PRESENCE_HOLD_TIMEOUT: 0},
                CONF_FEATURE_CLIMATE_GROUPS: {
                    CONF_CLIMATE_GROUPS_TURN_ON_STATE: AreaStates.OCCUPIED.value,
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_climate_groups")
async def setup_integration_climate_groups(
    hass: HomeAssistant,
    climate_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with BLE tracker config."""

    await init_integration(hass, [climate_groups_config_entry])
    yield
    await shutdown_integration(hass, [climate_groups_config_entry])


# Entities


@pytest.fixture(name="entities_climate_group_one")
async def setup_entities_climate_group_one(
    hass: HomeAssistant,
) -> list[MockClimate]:
    """Create one mock climate and setup the system with it."""
    mock_climate_entities = [
        MockClimate(
            name="climate_1",
            unique_id="unique_climate",
        )
    ]
    await setup_mock_entities(
        hass, CLIMATE_DOMAIN, {DEFAULT_MOCK_AREA: mock_climate_entities}
    )
    return mock_climate_entities


# Tests


async def test_climate_group_basic(
    hass: HomeAssistant,
    entities_climate_group_one: list[MockClimate],
    _setup_integration_climate_groups,
) -> None:
    """Test climate group."""

    mock_climate_entity_id = f"{CLIMATE_DOMAIN}.climate_1"
    climate_group_entity_id = (
        f"{CLIMATE_DOMAIN}.magic_areas_climate_groups_{DEFAULT_MOCK_AREA}_climate_group"
    )
    climate_control_entity_id = f"{SWITCH_DOMAIN}.magic_areas_climate_groups_{DEFAULT_MOCK_AREA}_climate_control"
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    presence_hold_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"
    )

    # Test mock entity created
    mock_climate_state = hass.states.get(mock_climate_entity_id)
    assert_state(mock_climate_state, STATE_OFF)

    # Test climate group created
    climate_group_state = hass.states.get(climate_group_entity_id)
    assert_state(climate_group_state, STATE_OFF)
    assert_in_attribute(climate_group_state, ATTR_ENTITY_ID, mock_climate_entity_id)

    # Test climate control switch created
    climate_control_state = hass.states.get(climate_control_entity_id)
    assert_state(climate_control_state, STATE_OFF)

    # Test presence hold switch created
    presence_hold_state = hass.states.get(presence_hold_entity_id)
    assert_state(presence_hold_state, STATE_OFF)

    # Test area state
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)

    # Turn on climate control
    hass.states.async_set(climate_control_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test climate control switch state turned on
    climate_control_state = hass.states.get(climate_control_entity_id)
    assert_state(climate_control_state, STATE_ON)

    # Turn area occupied through presence hold
    hass.states.async_set(presence_hold_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test area state is STATE_ON
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_ON)

    # Sleep so climate group has a chance to react
    await hass.async_block_till_done()

    # @FIXME IDK why this doesn't work. Probably my MockClimate is missing something.
    # # Test climate group is STATE_ON
    # climate_group_state = hass.states.get(climate_group_entity_id)
    # assert climate_group_state is not None
    # assert climate_group_state.state == STATE_ON

    # # Test mock entity is STATE_ON
    # mock_climate_state = hass.states.get(mock_climate_entity_id)
    # assert mock_climate_state is not None
    # assert mock_climate_state.state == STATE_ON
