import voluptuous as vol
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_LIGHT,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PRESENCE,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_WINDOW,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    STATE_ALARM_TRIGGERED,
    STATE_HOME,
    STATE_ON,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_PROBLEM,
)
from homeassistant.helpers import config_validation as cv

DOMAIN = "magic_areas"
MODULE_DATA = f"{DOMAIN}_data"

# MagicAreas Components
MAGIC_AREAS_COMPONENTS = [
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    SENSOR_DOMAIN,
]

# Configuration parameters
CONF_CONTROL_CLIMATE, DEFAULT_CONTROL_CLIMATE = "control_climate", True  # cv.boolean
CONF_CONTROL_LIGHTS, DEFAULT_CONTROL_LIGHTS = "control_lights", True  # cv.boolean
CONF_CONTROL_MEDIA, DEFAULT_CONTROL_MEDIA = "control_media", True  # cv.boolean
CONF_AUTO_LIGHTS = "automatic_lights"  # cv.entity_ids
CONF_INCLUDE_ENTITIES = "include_entities"  # cv.entity_ids
CONF_EXCLUDE_ENTITIES = "exclude_entities"  # cv.entity_ids
CONF_EXTERIOR, DEFAULT_EXTERIOR = "exterior", False  # cv.boolean
(
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
) = "presence_sensor_device_class", [
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PRESENCE,
]  # cv.list
CONF_ON_STATES, DEFAULT_ON_STATES = "on_states", [
    STATE_ON,
    STATE_HOME,
    STATE_PLAYING,
    STATE_OPEN,
]  # cv.list
CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT = "clear_timeout", 60  # cv.positive_int
CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL = "update_interval", 15  # cv.positive_int
CONF_ICON, DEFAULT_ICON = "icon", "mdi:texture-box"  # cv.string

# automatic_lights options
CONF_AL_DISABLE_ENTITY = "disable_entity"
CONF_AL_DISABLE_STATE, DEFAULT_AL_DISABLE_STATE = "disable_state", STATE_ON
CONF_AL_SLEEP_ENTITY = "sleep_entity"
CONF_AL_SLEEP_STATE, DEFAULT_AL_SLEEP_STATE = "sleep_state", STATE_ON
CONF_AL_SLEEP_LIGHTS = "sleep_lights"
CONF_AL_SLEEP_TIMEOUT = "sleep_timeout"
CONF_AL_ENTITIES = "entities"

# Health related
PRESENCE_DEVICE_COMPONENTS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
]  # @todo make configurable

AGGREGATE_BINARY_SENSOR_CLASSES = [
    DEVICE_CLASS_WINDOW,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_LIGHT,
]

DISTRESS_SENSOR_CLASSES = [
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_GAS,
]  # @todo make configurable
DISTRESS_STATES = [STATE_ALARM_TRIGGERED, STATE_ON, STATE_PROBLEM]

# Aggregates
AGGREGATE_SENSOR_CLASSES = (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
)

# Config Schema
# Auto Lights setting
CONFIG_AL_SCHEMA = vol.Any(
    {
        vol.Optional(CONF_AL_DISABLE_ENTITY): cv.entity_id,
        vol.Optional(
            CONF_AL_DISABLE_STATE, default=DEFAULT_AL_DISABLE_STATE
        ): cv.string,
        vol.Optional(CONF_AL_SLEEP_ENTITY): cv.entity_id,
        vol.Optional(CONF_AL_SLEEP_STATE, default=DEFAULT_AL_SLEEP_STATE): cv.string,
        vol.Optional(CONF_AL_SLEEP_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_AL_SLEEP_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_AL_ENTITIES, default=[]): cv.entity_ids,
    }
)
# Magic Areas
_DOMAIN_SCHEMA = vol.Schema(
    {
        cv.slug: vol.Any(
            {
                vol.Optional(
                    CONF_CONTROL_CLIMATE, default=DEFAULT_CONTROL_CLIMATE
                ): cv.boolean,
                vol.Optional(
                    CONF_CONTROL_LIGHTS, default=DEFAULT_CONTROL_LIGHTS
                ): cv.boolean,
                vol.Optional(
                    CONF_CONTROL_MEDIA, default=DEFAULT_CONTROL_MEDIA
                ): cv.boolean,
                vol.Optional(CONF_AUTO_LIGHTS, default=dict): CONFIG_AL_SCHEMA,
                vol.Optional(
                    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
                    default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
                ): cv.ensure_list,
                vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
                vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
                vol.Optional(CONF_EXTERIOR, default=DEFAULT_EXTERIOR): cv.boolean,
                vol.Optional(CONF_ON_STATES, default=DEFAULT_ON_STATES): cv.ensure_list,
                vol.Optional(
                    CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
                ): cv.positive_int,
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): cv.positive_int,
                vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
            },
            None,
        )
    }
)

# Autolights States
AUTOLIGHTS_STATE_SLEEP = "sleep"
AUTOLIGHTS_STATE_NORMAL = "enabled"
AUTOLIGHTS_STATE_DISABLED = "disabled"
