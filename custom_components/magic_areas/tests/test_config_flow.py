"""Tests for the config flow."""

from unittest.mock import patch

from custom_components.magic_areas.const import (
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_ICON,
    CONF_ID,
    CONF_NAME,
    CONF_ON_STATES,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
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

    with patch(
        "custom_components.magic_areas.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "kitchen",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "kitchen"
    assert result2["data"] == {
        CONF_NAME: "kitchen",
        CONF_CLEAR_TIMEOUT: 60,
        CONF_EXCLUDE_ENTITIES: [],
        CONF_ENABLED_FEATURES: {},
        CONF_ICON: "mdi:texture-box",
        CONF_UPDATE_INTERVAL: 60,
        CONF_ID: "kitchen",
        CONF_ON_STATES: ["on", "open"],
        CONF_TYPE: "meta",
    }
    assert len(mock_setup_entry.mock_calls) == 1
