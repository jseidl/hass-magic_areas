"""Magic Areas component for Homme Assistant."""

# @todo presence hold switch
# @todo light groups

import asyncio
import logging
from copy import deepcopy

import voluptuous as vol

# from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
# from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.helpers.entity import Entity
from homeassistant.setup import async_setup_component
from homeassistant.util import slugify

from .const import (
    _DOMAIN_SCHEMA,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    DOMAIN,
    MAGIC_AREAS_COMPONENTS,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: _DOMAIN_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up areas."""

    # Load registries
    area_registry = await hass.helpers.area_registry.async_get_registry()
    device_registry = await hass.helpers.device_registry.async_get_registry()
    entity_registry = await hass.helpers.entity_registry.async_get_registry()

    # Create device_id -> area_id map
    device_area_map = {}

    for device_id, device_object in device_registry.devices.items():
        if device_object.area_id:
            device_area_map[device_id] = device_object.area_id

    # Load entities and group by area
    area_entity_map = {}
    standalone_entities = {}

    for entity_id, entity_object in entity_registry.entities.items():

        # Skip disabled entities
        if entity_object.disabled:
            continue

        # Skip entities without devices, add them to a standalone map
        if entity_object.device_id not in device_area_map.keys():
            standalone_entities[entity_object.entity_id] = entity_object
            continue

        area_id = device_area_map[entity_object.device_id]

        _LOGGER.info(f"Area {area_id} entity {entity_object.entity_id}")

        copied_object = deepcopy(entity_object)

        if area_id not in area_entity_map.keys():
            area_entity_map[area_id] = []

        area_entity_map[area_id].append(copied_object)

    # Populate MagicAreas
    magic_areas = []
    areas = area_registry.async_list_areas()

    magic_areas_config = config[DOMAIN]

    for area in areas:

        area_entities = (
            area_entity_map[area.id] if area.id in area_entity_map.keys() else []
        )

        entity_count = len(area_entities)
        _LOGGER.info(
            f"Creating area '{area.name}' (#{area.id}) with {entity_count} entities."
        )
        magic_area = MagicArea(
            hass,
            area.id,
            area.name,
            area_entities,
            magic_areas_config,
            standalone_entities,
        )
        magic_areas.append(magic_area)

        # Never got this to work... @jseidl
        # # Create Light Groups
        # if LIGHT_DOMAIN in magic_area.entities.keys():
        #     light_entities = [e.entity_id for e in magic_area.entities[LIGHT_DOMAIN]]

        #     le_txt = ", ".join(light_entities)
        #     _LOGGER.info(f"Light groups for {magic_area.name}: {le_txt}")

        #     await async_setup_component(
        #         hass,
        #         LIGHT_DOMAIN,
        #         {
        #             LIGHT_DOMAIN: {
        #                 "platform": GROUP_DOMAIN,
        #                 "entities": light_entities,
        #                 "name": f"{area.name} Lights"
        #             }
        #         },
        #     )

    hass.data[MODULE_DATA] = magic_areas

    # Load platforms
    for component in MAGIC_AREAS_COMPONENTS:
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform(component, DOMAIN, {}, config)
        )

    return True


# Classes
# StandaloneEntity mock class
class StandaloneEntity(Entity):
    def __init__(self, hass, entity_id):

        self.hass = hass
        self.entity_id = entity_id
        self._device_class = None

        # Try to fetch device_class from attributes
        try:
            entity_state = hass.states.get(self.entity_id)
            if "device_class" in entity_state.attributes.keys():
                self._device_class = entity_state.attributes["device_class"]
        except Exception as e:
            str_err = str(e)
            _LOGGER.warn(
                f"Error retrieving device_class for entity '{self.entity_id}': str_err"
            )

    @property
    def device_class(self):

        return self._device_class


class MagicArea(object):
    def __init__(self, hass, id, name, entities, config, standalone_entities):

        self.hass = hass
        self.name = name
        self.id = id
        self.slug = slugify(name)

        # Check if area is defined on YAML, if not, generate default config
        if self.slug not in config.keys():
            default_config = {f"{self.slug}": {}}
            self.config = _DOMAIN_SCHEMA(default_config)[self.slug]
        else:
            self.config = config[self.slug]

        self.entities = {}

        filtered_entities = self.filter_entities(entities, standalone_entities)

        self.organize_entities(filtered_entities)

        self.debug_show()

    def debug_show(self):

        _LOGGER.info(f"{self.name} ({self.slug}) loaded")

        for platform, entities in self.entities.items():
            ec = len(entities)
            _LOGGER.info(f"> {platform}: {ec}")
            for entity in entities:
                _LOGGER.info(f"  - {entity.entity_id}")

    # Filter (include/exclude) entities
    def filter_entities(self, area_entities, standalone_entities):

        filtered_entities = []

        for entity in area_entities:

            # Exclude
            if entity.entity_id in self.config.get(CONF_EXCLUDE_ENTITIES):
                _LOGGER.info(
                    f"Entity {entity.entity_id} excluded from {self.slug} area"
                )
                continue

            filtered_entities.append(entity)

        # Include entities not tied to devices (MQTT/Input*/Template)
        standalone_entities_count = len(standalone_entities)

        if standalone_entities_count:
            for entity_id in self.config.get(CONF_INCLUDE_ENTITIES):
                if entity_id in standalone_entities.keys():
                    filtered_entities.append(standalone_entities[entity_id])
                else:
                    # Entity not in registry, call hass
                    standalone_entity = StandaloneEntity(self.hass, entity_id)
                    filtered_entities.append(standalone_entity)

        return filtered_entities

    # Organize entities into their platforms (media_player/light/sensor/binary_sensor etc)
    def organize_entities(self, entities):

        for entity in entities:

            entity_component, entity_slug = entity.entity_id.split(".")

            if entity_component not in self.entities.keys():
                self.entities[entity_component] = []

            self.entities[entity_component].append(entity)
