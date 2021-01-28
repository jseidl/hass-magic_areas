import voluptuous as vol
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_LIGHT,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_PRESENCE,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_WINDOW,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
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

# Magic Areas Events
EVENT_MAGICAREAS_STARTED = "magicareas_start"
EVENT_MAGICAREAS_READY = "magicareas_ready"
EVENT_MAGICAREAS_AREA_READY = "magicareas_area_ready"

DEVICE_CLASS_DOMAINS = (BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN)

ALL_BINARY_SENSOR_DEVICE_CLASSES = (
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
    DEVICE_CLASS_POWER,
)

# Data Items
DATA_AREA_OBJECT = "area_object"
DATA_UNDO_UPDATE_LISTENER = "undo_update_listener"

# MagicAreas Components
MAGIC_AREAS_COMPONENTS = [
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_META = [
    BINARY_SENSOR_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_GLOBAL = MAGIC_AREAS_COMPONENTS_META + [MEDIA_PLAYER_DOMAIN]

# Meta Areas
META_AREA_GLOBAL = "Global"
META_AREA_INTERIOR = "Interior"
META_AREA_EXTERIOR = "Exterior"
META_AREAS = [META_AREA_GLOBAL, META_AREA_INTERIOR, META_AREA_EXTERIOR]

# Area Types
AREA_TYPE_META = "meta"
AREA_TYPE_INTERIOR = "interior"
AREA_TYPE_EXTERIOR = "exterior"
AREA_TYPES = [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR, AREA_TYPE_META]

# Configuration parameters
CONF_ID = "id"
CONF_NAME, DEFAULT_NAME = "name", ""  # cv.string
CONF_TYPE, DEFAULT_TYPE = "type", AREA_TYPE_INTERIOR  # cv.string
CONF_ENABLED_FEATURES, DEFAULT_ENABLED_FEATURES = "features", []  # cv.list
CONF_INCLUDE_ENTITIES = "include_entities"  # cv.entity_ids
CONF_EXCLUDE_ENTITIES = "exclude_entities"  # cv.entity_ids
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
CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES = (
    "aggregates_min_entities",
    2,
)  # cv.positive_int
CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT = "clear_timeout", 60  # cv.positive_int
CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL = "update_interval", 60  # cv.positive_int
CONF_ICON, DEFAULT_ICON = "icon", "mdi:texture-box"  # cv.string
CONF_NOTIFICATION_DEVICES = "notification_devices"  # cv.entity_ids
CONF_NOTIFY_ON_SLEEP, DEFAULT_NOTIFY_ON_SLEEP = "notify_on_sleep", False  # cv.bool
# features
CONF_FEATURE_CLIMATE_CONTROL = "control_climate"
CONF_FEATURE_LIGHT_CONTROL = "control_lights"
CONF_FEATURE_MEDIA_CONTROL = "control_media"
CONF_FEATURE_LIGHT_GROUPS = "light_groups"
CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER = "area_aware_media_player"
CONF_FEATURE_AGGREGATION = "aggregates"
CONF_FEATURE_HEALTH = "health"

CONF_FEATURE_LIST = [
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_LIGHT_CONTROL,
    CONF_FEATURE_MEDIA_CONTROL,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
]

CONF_FEATURE_LIST_META = [
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
]

CONF_FEATURE_LIST_GLOBAL = CONF_FEATURE_LIST_META + [
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
]

# automatic_lights options
CONF_NIGHT_ENTITY = "night_entity"
CONF_NIGHT_STATE, DEFAULT_NIGHT_STATE = "night_state", STATE_ON
CONF_MAIN_LIGHTS = "main_lights"  # cv.entity_ids
CONF_SLEEP_LIGHTS = "sleep_lights"
CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT = "sleep_timeout", 0  # int
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_SLEEP_STATE, DEFAULT_SLEEP_STATE = "sleep_state", STATE_ON

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

AGGREGATE_MODE_SUM = [DEVICE_CLASS_POWER, DEVICE_CLASS_CURRENT, DEVICE_CLASS_ENERGY]

# Config Schema

# Magic Areas
_AREA_SCHEMA = {
    # vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_ENABLED_FEATURES, default=[]): cv.ensure_list,
    vol.Optional(
        CONF_PRESENCE_SENSOR_DEVICE_CLASS,
        default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
    ): cv.ensure_list,
    vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
    vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
    vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): str,
    vol.Optional(CONF_ON_STATES, default=DEFAULT_ON_STATES): cv.ensure_list,
    vol.Optional(
        CONF_AGGREGATES_MIN_ENTITIES, default=DEFAULT_AGGREGATES_MIN_ENTITIES
    ): cv.positive_int,
    vol.Optional(CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT): cv.positive_int,
    vol.Optional(
        CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
    ): cv.positive_int,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    vol.Optional(CONF_NOTIFICATION_DEVICES, default=[]): cv.entity_ids,
    vol.Optional(CONF_NOTIFY_ON_SLEEP, default=DEFAULT_NOTIFY_ON_SLEEP): bool,
    vol.Optional(CONF_NIGHT_ENTITY): cv.entity_id,
    vol.Optional(CONF_NIGHT_STATE, default=DEFAULT_NIGHT_STATE): str,
    vol.Optional(CONF_SLEEP_ENTITY): cv.entity_id,
    vol.Optional(CONF_SLEEP_STATE, default=DEFAULT_SLEEP_STATE): str,
    vol.Optional(CONF_SLEEP_TIMEOUT, default=DEFAULT_SLEEP_TIMEOUT): cv.positive_int,
    vol.Optional(CONF_MAIN_LIGHTS, default=[]): cv.entity_ids,
    vol.Optional(CONF_SLEEP_LIGHTS, default=[]): cv.entity_ids,
}

_DOMAIN_SCHEMA = vol.Schema({cv.slug: vol.Any(_AREA_SCHEMA, None)})
# Autolights States
AUTOLIGHTS_STATE_SLEEP = "sleep"
AUTOLIGHTS_STATE_NORMAL = "enabled"
AUTOLIGHTS_STATE_DISABLED = "disabled"

# VALIDATION_TUPLES
VALIDATION_TUPLES = [
    (CONF_ENABLED_FEATURES, DEFAULT_ENABLED_FEATURES, cv.ensure_list),
    (CONF_INCLUDE_ENTITIES, [], cv.entity_ids),
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
    (
        CONF_PRESENCE_SENSOR_DEVICE_CLASS,
        DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        cv.ensure_list,
    ),
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_ICON, DEFAULT_ICON, str),
    (CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES, int),
    (CONF_NOTIFICATION_DEVICES, [], cv.entity_ids),
    (CONF_NOTIFY_ON_SLEEP, DEFAULT_NOTIFY_ON_SLEEP, bool),
    (CONF_NIGHT_ENTITY, "", cv.entity_id),
    (CONF_NIGHT_STATE, DEFAULT_NIGHT_STATE, str),
    (CONF_MAIN_LIGHTS, [], cv.entity_ids),
    (CONF_SLEEP_LIGHTS, [], cv.entity_ids),
    (
        CONF_SLEEP_ENTITY,
        "",
        cv.entity_id,
    ),
    (CONF_SLEEP_STATE, DEFAULT_SLEEP_STATE, str),
    (CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
    (CONF_TYPE, DEFAULT_TYPE, str),
]

VALIDATION_TUPLES_META = [
    (CONF_ENABLED_FEATURES, DEFAULT_ENABLED_FEATURES, cv.ensure_list),
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_ICON, DEFAULT_ICON, str),
    (CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
]
