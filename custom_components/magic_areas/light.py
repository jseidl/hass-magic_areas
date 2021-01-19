DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

from .const import MODULE_DATA

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument

    areas = hass.data.get(MODULE_DATA)

    light_groups = []

    _LOGGER.info("Creating light groups")

    for area in areas:

        # Create Light Groups
        if LIGHT_DOMAIN in area.entities.keys():

            light_entities = [e.entity_id for e in area.entities[LIGHT_DOMAIN]]
            group_name = f"{area.name} Lights"

            _LOGGER.info(f"Creating light group '{group_name}' for area {area.slug}")

            light_groups.append(LightGroup(group_name, light_entities))

    if light_groups:
        async_add_entities(light_groups)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)
