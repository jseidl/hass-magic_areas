"""Tests for the config flow."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.simply_magic_areas.const import (
    AREA_TYPE_INTERIOR,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    CONF_ICON,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_NAME,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.area_registry import async_get as async_get_ar


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    # Create an area in the registry.
    registry = async_get_ar(hass)
    registry.async_get_or_create("kitchen")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_NAME: "kitchen"},
    )
    await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "kitchen"
    assert result2["data"] == {
        CONF_NAME: "kitchen",
        CONF_CLEAR_TIMEOUT: 60,
        CONF_ENABLED_FEATURES: {},
        CONF_ICON: "mdi:texture-box",
        CONF_ID: "kitchen",
        CONF_TYPE: AREA_TYPE_INTERIOR,
        "accented_entity": "",
        "accented_state_dim": 0,
        "bright_entity": "",
        "bright_state_dim": 0,
        "sleep_entity": "",
        "sleep_state_dim": 30,
        "extended_state_dim": 0,
        "clear_state_dim": 0,
        "occupied_state_dim": 100,
    }
    # assert len(mock_setup_entry.mock_calls) == 1


async def test_options(hass: HomeAssistant, config_entry: MockConfigEntry) -> None:
    """Test we get the form."""
    # Create an area in the registry.
    registry = async_get_ar(hass)
    registry.async_get_or_create("kitchen")
    config_entry.add_to_hass(hass)

    # Load the integration
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    # submit form with options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_CLEAR_TIMEOUT: 12}
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_features"
    assert result["errors"] is None
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # assert result["title"] == "kitchen"
    assert result["data"] == {
        CONF_CLEAR_TIMEOUT: 12,
        CONF_ENABLED_FEATURES: {},
        CONF_ICON: "mdi:texture-box",
        CONF_TYPE: AREA_TYPE_INTERIOR,
        "accented_entity": "",
        "accented_state_dim": 0.0,
        "bright_entity": "",
        "bright_state_dim": 0.0,
        "sleep_entity": "",
        "sleep_state_dim": 30.0,
        "extended_state_dim": 0.0,
        "clear_state_dim": 0.0,
        "occupied_state_dim": 100.0,
    }


async def test_options_enable_advanced_lights(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """Test we get the form."""
    # Create an area in the registry.
    registry = async_get_ar(hass)
    registry.async_get_or_create("kitchen")
    config_entry.add_to_hass(hass)

    # Load the integration
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "area_config"
    assert result["data_schema"]({}) == {
        "accented_entity": "",
        "accented_state_dim": 0.0,
        "bright_entity": "",
        "bright_state_dim": 0.0,
        "clear_state_dim": 0.0,
        "clear_timeout": 60.0,
        "extended_state_dim": 0.0,
        CONF_ICON: "mdi:texture-box",
        "occupied_state_dim": 100.0,
        "sleep_entity": "",
        "sleep_state_dim": 30.0,
        CONF_TYPE: "interior",
    }

    # submit form with options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={CONF_CLEAR_TIMEOUT: 12}
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "select_features"
    assert result["errors"] is None

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_FEATURE_ADVANCED_LIGHT_GROUPS: True},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "feature_conf_advanced_light_groups"
    assert result["errors"] == {}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"accented_state_check": STATE_OFF},
    )
    await hass.async_block_till_done()
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # assert result["title"] == "kitchen"
    assert result["data"] == {
        CONF_CLEAR_TIMEOUT: 12,
        CONF_ENABLED_FEATURES: {
            CONF_FEATURE_ADVANCED_LIGHT_GROUPS: {
                "accented_lights": [],
                "accented_state_check": STATE_OFF,
                "bright_lights": [],
                "bright_state_check": STATE_ON,
                "clear_lights": [],
                "clear_state_check": STATE_ON,
                "sleep_lights": [],
                "sleep_state_check": STATE_ON,
                "extended_lights": [],
                "extended_state_check": STATE_ON,
                "occupied_lights": [],
                "occupied_state_check": STATE_ON,
                CONF_EXCLUDE_ENTITIES: [],
                CONF_PRESENCE_DEVICE_PLATFORMS: [
                    MEDIA_PLAYER_DOMAIN,
                    BINARY_SENSOR_DOMAIN,
                ],
                CONF_PRESENCE_SENSOR_DEVICE_CLASS: [
                    BinarySensorDeviceClass.MOTION,
                    BinarySensorDeviceClass.OCCUPANCY,
                    BinarySensorDeviceClass.PRESENCE,
                ],
                CONF_UPDATE_INTERVAL: 60,
                CONF_ON_STATES: [STATE_ON, STATE_OPEN],
                CONF_INCLUDE_ENTITIES: [],
            },
        },
        CONF_ICON: "mdi:texture-box",
        CONF_TYPE: AREA_TYPE_INTERIOR,
        "accented_entity": "",
        "accented_state_dim": 0.0,
        "bright_entity": "",
        "bright_state_dim": 0.0,
        "sleep_entity": "",
        "sleep_state_dim": 30.0,
        "extended_state_dim": 0.0,
        "clear_state_dim": 0.0,
        "occupied_state_dim": 100.0,
    }
