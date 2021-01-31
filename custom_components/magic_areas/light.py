DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

from .const import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_LIGHT_GROUPS,
    DATA_AREA_OBJECT,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Check feature availability
    if not area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        return

    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug(f"No {LIGHT_DOMAIN} entities for area {area.name} ")
        return

    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]
    group_name = f"{area.name} Lights"

    # Check CONF_AGGREGATES_MIN_ENTITIES
    if len(light_entities) < area.config.get(CONF_AGGREGATES_MIN_ENTITIES):
        _LOGGER.debug(f"Not enough entities for Light group for area {area.name}")
        return

    # Create Light Group
    _LOGGER.debug(
        f"Creating light groups for area {area.name} with lights: {light_entities}"
    )
    async_add_entities([LightGroup(group_name, light_entities)])
