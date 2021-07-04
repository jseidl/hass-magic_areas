DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

from .const import (
    CONF_FEATURE_LIGHT_GROUPS,
    LIGHT_GROUP_CATEGORIES,
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

    if not light_entities:
        _LOGGER.debug(f"Not enough entities for Light group for area {area.name}")
        return

    light_groups = []

    # Create All light group
    _LOGGER.debug(
        f"Creating Area light group for area {area.name} with lights: {light_entities}"
    )
    light_groups.append(LightGroup(f"{area.name} Lights", light_entities))

    # Create extended light groups
    for category in LIGHT_GROUP_CATEGORIES:
        category_lights = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(category)

        if category_lights:
            category_title = ' '.join(category.split('_')).title()
            _LOGGER.debug(f"Creating {category_title} group for area {area.name} with lights: {category_lights}")
            light_groups.append(LightGroup(f"{category_title} ({area.name})", category_lights))

    # Create all groups
    async_add_entities(light_groups)
