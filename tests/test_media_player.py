"""Test for aggregate (group) sensor behavior."""

import asyncio
import logging

from homeassistant.const import STATE_PLAYING
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN

from homeassistant.core import HomeAssistant

from .mocks import MockMediaPlayer

_LOGGER = logging.getLogger(__name__)


async def test_area_aware_media_player(
    hass: HomeAssistant,
    entities_sensor_illuminance_multiple: list[MockMediaPlayer],
    _setup_integration_area_aware_media_player,
) -> None:
    """Test the area aware media player."""

    area_aware_media_player_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_threshold_kitchen_threshold_light"
    )

    area_sensor_entity_id = (
        f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_kitchen_area_state"
    )

    ## Test area clear

    # Ensure area is clear

    # Send play to AAMP

    # Ensure area MP is NOT playing

    # Turn off AAMP

    ## Test area occupied

    # Ensure area is occupied

    # Send play to AAMP

    # Ensure area MP is playing

    # Turn off AAMP

    ## Test area occupied + sleep

    # Ensure area is occupied + sleep

    # Send play to AAMP

    # Ensure area MP is NOT playing

    # Turn off AAMP