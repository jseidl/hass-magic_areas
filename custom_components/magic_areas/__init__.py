"""Magic Areas component for Homme Assistant."""

# @todo presence hold switch
# @todo light groups

import logging
import asyncio
import voluptuous as vol

from copy import deepcopy

from homeassistant.setup import async_setup_component
from homeassistant.helpers import config_validation as cv
from homeassistant.const import (STATE_ON, STATE_HOME, STATE_OPEN, STATE_PLAYING)
#from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.group import DOMAIN as GROUP_DOMAIN
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    DEVICE_CLASS_PRESENCE,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_MOTION,
)
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

DOMAIN = "magic_areas"
MODULE_DATA = f"{DOMAIN}_data"

# MagicAreas Components
MAGIC_AREAS_COMPONENTS = [
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
]

# Configuration parameters
CONF_CONTROL_CLIMATE = "control_climate" # cv.boolean
CONF_CONTROL_LIGHTS = "control_lights" # cv.boolean
CONF_CONTROL_MEDIA = "control_media" # cv.boolean
CONF_AUTO_LIGHTS = "automatic_lights" # cv.entity_ids
CONF_INCLUDE_ENTITIES = "include_entities" # cv.entity_ids
CONF_EXCLUDE_ENTITIES = "exclude_entities" # cv.entity_ids
CONF_PRESENCE_SENSOR_DEVICE_CLASS = "presence_sensor_device_class"
CONF_ON_STATES  = "on_states" # cv.list
CONF_CLEAR_TIMEOUT  = "clear_timeout" # cv.positive_int
CONF_UPDATE_INTERVAL  = "update_interval" # cv.positive_int
CONF_ICON = "icon" # cv.string

# Defaults
DEFAULT_CONTROL_CLIMATE = True
DEFAULT_CONTROL_LIGHTS = True
DEFAULT_CONTROL_MEDIA = True
DEFAULT_CLEAR_TIMEOUT = 5
DEFAULT_UPDATE_INTERVAL = 15
DEFAULT_ICON = "mdi:texture-box"
DEFAULT_ON_STATES = [STATE_ON, STATE_HOME, STATE_PLAYING, STATE_OPEN]
DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS = [DEVICE_CLASS_MOTION, DEVICE_CLASS_OCCUPANCY, DEVICE_CLASS_PRESENCE]

# Config Schema
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.slug: vol.Any(
                    {
                        vol.Optional(CONF_CONTROL_CLIMATE, default=DEFAULT_CONTROL_CLIMATE): cv.boolean,
                        vol.Optional(CONF_CONTROL_LIGHTS, default=DEFAULT_CONTROL_LIGHTS): cv.boolean,
                        vol.Optional(CONF_CONTROL_MEDIA, default=DEFAULT_CONTROL_MEDIA): cv.boolean,
                        vol.Optional(CONF_AUTO_LIGHTS, default=[]): cv.entity_ids,
                        vol.Optional(CONF_PRESENCE_SENSOR_DEVICE_CLASS, default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS): cv.ensure_list,
                        vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
                        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
                        vol.Optional(CONF_ON_STATES, default=DEFAULT_ON_STATES): cv.ensure_list,
                        vol.Optional(CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT): cv.positive_int,
                        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): cv.positive_int,
                        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
                    },
                    None,
                )
            }
        )
    },
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

        # Skip devices without areas, add them to a standalone map
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

        area_entities = area_entity_map[area.id] if area.id in area_entity_map.keys() else []

        entity_count = len(area_entities)
        _LOGGER.info(f"Creating area '{area.name}' (#{area.id}) with {entity_count} entities.")
        magic_area = MagicArea(hass, area.id, area.name, area_entities, magic_areas_config, standalone_entities)
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

class MagicArea(object):

    def __init__(self, hass, id, name, entities, config, standalone_entities):

        self.hass               = hass
        self.name               = name
        self.slug               = slugify(name)
        self.config             = config

        self.control_lights     = DEFAULT_CONTROL_LIGHTS
        self.control_climate    = DEFAULT_CONTROL_CLIMATE
        self.control_media      = DEFAULT_CONTROL_MEDIA

        self.presence_device_class = DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS

        self.automatic_lights   = []
        self.include_entities   = []
        self.exclude_entities   = []
        self.clear_timeout      = DEFAULT_CLEAR_TIMEOUT
        self.update_interval    = DEFAULT_UPDATE_INTERVAL
        self.icon               = DEFAULT_ICON
        self.on_states          = DEFAULT_ON_STATES

        self.entities           = {}

        self.load_config()

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

    # Load config overrides if present
    def load_config(self):

        if self.slug in self.config.keys():
            _LOGGER.info(f"Config override founnd for {self.slug}")
            area_config = self.config[self.slug]

            self.control_lights         = area_config.get(CONF_CONTROL_LIGHTS)
            self.control_climate        = area_config.get(CONF_CONTROL_CLIMATE)
            self.control_media          = area_config.get(CONF_CONTROL_MEDIA)
            self.automatic_lights       = area_config.get(CONF_AUTO_LIGHTS)
            self.presence_device_class  = area_config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS)
            self.exclude_entities       = area_config.get(CONF_EXCLUDE_ENTITIES)
            self.include_entities       = area_config.get(CONF_INCLUDE_ENTITIES)
            self.update_interval        = area_config.get(CONF_UPDATE_INTERVAL)
            self.clear_timeout          = area_config.get(CONF_CLEAR_TIMEOUT)
            self.on_states              = area_config.get(CONF_ON_STATES)
            self.icon                   = area_config.get(CONF_ICON)

    # Filter (include/exclude) entities
    def filter_entities(self, area_entities, standalone_entities):
        
        filtered_entities = []
        
        for entity in area_entities:

                # Exclude
                if entity.entity_id in self.exclude_entities:
                    _LOGGER.info(f"Entity {entity.entity_id} excluded from {self.slug} area")
                    continue

                filtered_entities.append(entity)

        # Include entities not tied to devices (MQTT/Input*/Template)
        standalone_entities_count = len(standalone_entities)

        if standalone_entities_count:
            for entity_id in self.include_entities:
                if entity_id in standalone_entities.keys():
                    filtered_entities.append(standalone_entities[entity_id])

        return filtered_entities
            
    # Organize entities into their platforms (media_player/light/sensor/binary_sensor etc)
    def organize_entities(self, entities):

        for entity in entities:

            entity_component, entity_slug = entity.entity_id.split('.')

            if entity_component not in self.entities.keys():
                self.entities[entity_component] = []

            self.entities[entity_component].append(entity)