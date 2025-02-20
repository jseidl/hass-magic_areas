"""Test initializing the system."""

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant

from tests.common import assert_state

_LOGGER = logging.getLogger(__name__)


async def test_init_default_config(
    hass: HomeAssistant, basic_config_entry: MockConfigEntry, _setup_integration_basic
) -> None:
    """Test loading the integration."""

    # Validate the right enties were created.
    area_binary_sensor = hass.states.get(
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    assert_state(area_binary_sensor, STATE_OFF)
