"""Tests for the Fan groups feature."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.fan import DOMAIN as FAN_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import (
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_FAN_GROUPS,
    DOMAIN,
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
from tests.mocks import MockFan

# Fixtures


@pytest.fixture(name="fan_groups_config_entry")
def mock_config_entry_fan_groups() -> MockConfigEntry:
    """Fixture for mock configuration entry."""
    data = get_basic_config_entry_data(DEFAULT_MOCK_AREA)
    data.update({CONF_ENABLED_FEATURES: {CONF_FEATURE_FAN_GROUPS: {}}})
    return MockConfigEntry(domain=DOMAIN, data=data)


@pytest.fixture(name="_setup_integration_fan_groups")
async def setup_integration_fan_groups(
    hass: HomeAssistant,
    fan_groups_config_entry: MockConfigEntry,
) -> AsyncGenerator[Any]:
    """Set up integration with Fan groups config."""

    await init_integration(hass, [fan_groups_config_entry])
    yield
    await shutdown_integration(hass, [fan_groups_config_entry])


# Entities


@pytest.fixture(name="entities_fan_multiple")
async def setup_entities_fan_multiple(
    hass: HomeAssistant,
) -> list[MockFan]:
    """Create multiple mock fans setup the system with it."""
    mock_fan_entities: list[MockFan] = []
    nr_fans: int = 3
    for i in range(nr_fans):
        mock_fan_entities.append(
            MockFan(name=f"mock_fan_{i}", unique_id=f"unique_fan_{i}")
        )
    await setup_mock_entities(hass, FAN_DOMAIN, {DEFAULT_MOCK_AREA: mock_fan_entities})
    return mock_fan_entities


# Tests


async def test_fan_group_basic(
    hass: HomeAssistant,
    entities_fan_multiple: list[MockFan],
    _setup_integration_fan_groups,
) -> None:
    """Test Fan groups functionality."""

    fan_group_entity_id = (
        f"{FAN_DOMAIN}.magic_areas_fan_groups_{DEFAULT_MOCK_AREA}_fan_group_fan"
    )

    # Initialization test
    fan_group_state = hass.states.get(fan_group_entity_id)
    assert_state(fan_group_state, STATE_OFF)
    for fan_entity in entities_fan_multiple:
        assert_in_attribute(fan_group_state, ATTR_ENTITY_ID, fan_entity.entity_id)

    # Basic group test
    # Flip group on, check members
    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: fan_group_entity_id}
    )
    await hass.async_block_till_done()

    fan_group_state = hass.states.get(fan_group_entity_id)
    assert_state(fan_group_state, STATE_ON)

    for fan_entity in entities_fan_multiple:
        fan_entity_state = hass.states.get(fan_entity.entity_id)
        assert_state(fan_entity_state, STATE_ON)

    # Flip group off, check members
    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: fan_group_entity_id}
    )
    await hass.async_block_till_done()

    fan_group_state = hass.states.get(fan_group_entity_id)
    assert_state(fan_group_state, STATE_OFF)

    for fan_entity in entities_fan_multiple:
        fan_entity_state = hass.states.get(fan_entity.entity_id)
        assert_state(fan_entity_state, STATE_OFF)

    # Flip member on, check group
    first_fan_entity_id = entities_fan_multiple[0].entity_id
    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: first_fan_entity_id}
    )
    await hass.async_block_till_done()

    first_fan_state = hass.states.get(first_fan_entity_id)
    assert_state(first_fan_state, STATE_ON)

    fan_group_state = hass.states.get(fan_group_entity_id)
    assert_state(fan_group_state, STATE_ON)
