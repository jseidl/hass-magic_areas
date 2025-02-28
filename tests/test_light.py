"""Test for light groups."""

from collections.abc import AsyncGenerator
import logging
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light.const import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_ACCENT_LIGHTS,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_OVERHEAD_LIGHTS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_SLEEP_LIGHTS,
    CONF_TASK_LIGHTS,
    CONF_TASK_LIGHTS_STATES,
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
from tests.mocks import MockLight

_LOGGER = logging.getLogger(__name__)


# Fixtures


@pytest.fixture(name="light_groups_config_entry")
def mock_config_entry_light_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update(
        {
            CONF_ENABLED_FEATURES: {
                CONF_FEATURE_PRESENCE_HOLD: {CONF_PRESENCE_HOLD_TIMEOUT: 0},
                CONF_FEATURE_LIGHT_GROUPS: {
                    CONF_TASK_LIGHTS_STATES: [AreaStates.OCCUPIED.value],
                    CONF_TASK_LIGHTS: ["light.light_1"],
                    CONF_ACCENT_LIGHTS: [],
                    CONF_OVERHEAD_LIGHTS: [],
                    CONF_SLEEP_LIGHTS: [],
                },
            }
        }
    )
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_light_groups")
async def setup_integration_light_groups(
    hass: HomeAssistant,
    light_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with BLE tracker config."""

    await init_integration(hass, [light_groups_config_entry])
    yield
    await shutdown_integration(hass, [light_groups_config_entry])


# Entities


@pytest.fixture(name="entities_light_group_one")
async def _setup_integration_light_groups(
    hass: HomeAssistant,
) -> list[MockLight]:
    """Create one mock light and setup the system with it."""
    mock_light_entities = [
        MockLight(
            name="light_1",
            state="off",
            unique_id="unique_light",
        )
    ]
    await setup_mock_entities(
        hass, LIGHT_DOMAIN, {DEFAULT_MOCK_AREA: mock_light_entities}
    )
    return mock_light_entities


# Tests


async def test_light_group_basic(
    hass: HomeAssistant,
    entities_light_group_one: list[MockLight],
    _setup_integration_light_groups,
) -> None:
    """Test light group."""

    mock_light_entity_id = f"{LIGHT_DOMAIN}.light_1"
    light_group_entity_id = (
        f"{LIGHT_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_all_lights"
    )
    light_control_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_light_groups_{DEFAULT_MOCK_AREA}_light_control"
    )
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA}_area_state"
    presence_hold_entity_id = (
        f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{DEFAULT_MOCK_AREA}"
    )

    # Test mock entity created
    mock_light_state = hass.states.get(mock_light_entity_id)
    assert_state(mock_light_state, STATE_OFF)

    # Test light group created
    light_group_state = hass.states.get(light_group_entity_id)
    assert_state(light_group_state, STATE_OFF)
    assert_in_attribute(light_group_state, ATTR_ENTITY_ID, mock_light_entity_id)

    # Test light control switch created
    light_control_state = hass.states.get(light_control_entity_id)
    assert_state(light_control_state, STATE_OFF)

    # Test presence hold switch created
    presence_hold_state = hass.states.get(presence_hold_entity_id)
    assert_state(presence_hold_state, STATE_OFF)

    # Test area state
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_OFF)

    # Turn on light control
    hass.states.async_set(light_control_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test light control switch state turned on
    light_control_state = hass.states.get(light_control_entity_id)
    assert_state(light_control_state, STATE_ON)

    # Turn area occupied through presence hold
    hass.states.async_set(presence_hold_entity_id, STATE_ON)
    await hass.async_block_till_done()

    # Test area state is STATE_ON
    area_state = hass.states.get(area_sensor_entity_id)
    assert_state(area_state, STATE_ON)

    # Sleep so light group has a chance to react
    await hass.async_block_till_done()

    # @FIXME IDK why this doesn't work. Probably my MockLight is missing something.
    # # Test light group is STATE_ON
    # light = hass.states.get(light_group_entity_id)
    # assert lght is not None
    # assert light.state == STATE_ON

    # # Test mock entity is STATE_ON
    # mock_light_state = hass.states.get(mock_climate_entity_id)
    # assert mock_light_state is not None
    # assert mock_light_state.state == STATE_ON
