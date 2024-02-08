from itertools import chain

import voluptuous as vol
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.components.sun import DOMAIN as SUN_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    STATE_ALARM_TRIGGERED,
    STATE_HOME,
    STATE_ON,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import config_validation as cv

DOMAIN = "magic_areas"
MODULE_DATA = f"{DOMAIN}_data"

# Magic Areas Events
EVENT_MAGICAREAS_STARTED = "magicareas_start"
EVENT_MAGICAREAS_READY = "magicareas_ready"
EVENT_MAGICAREAS_AREA_READY = "magicareas_area_ready"
EVENT_MAGICAREAS_AREA_OCCUPIED = "magicareas_area_occupied"
EVENT_MAGICAREAS_AREA_CLEAR = "magicareas_area_clear"
EVENT_MAGICAREAS_AREA_STATE_CHANGED = "magicareas_area_state_changed"

ALL_BINARY_SENSOR_DEVICE_CLASSES = [cls.value for cls in BinarySensorDeviceClass]

# Data Items
DATA_AREA_OBJECT = "area_object"
DATA_UNDO_UPDATE_LISTENER = "undo_update_listener"

# Attributes
ATTR_STATES = "states"
ATTR_ON_STATES = "on_states"
ATTR_AREAS = "areas"
ATTR_ACTIVE_AREAS = "active_areas"
ATTR_TYPE = "type"
ATTR_UPDATE_INTERVAL = "update_interval"
ATTR_CLEAR_TIMEOUT = "clear_timeout"
ATTR_ACTIVE_SENSORS = "active_sensors"
ATTR_LAST_ACTIVE_SENSORS = "last_active_sensors"
ATTR_FEATURES = "features"
ATTR_PRESENCE_SENSORS = "presence_sensors"

# Icons
ICON_PRESENCE_HOLD = "mdi:car-brake-hold"
ICON_LIGHT_CONTROL = "mdi:lightbulb-auto-outline"

# Area States
AREA_STATE_CLEAR = "clear"
AREA_STATE_OCCUPIED = "occupied"
AREA_STATE_EXTENDED = "extended"
AREA_STATE_DARK = "dark"
AREA_STATE_BRIGHT = "bright"
AREA_STATE_SLEEP = "sleep"
AREA_STATE_ACCENT = "accented"

AREA_PRIORITY_STATES = [AREA_STATE_SLEEP, AREA_STATE_ACCENT]

BUILTIN_AREA_STATES = [AREA_STATE_OCCUPIED, AREA_STATE_EXTENDED]
CONFIGURABLE_AREA_STATES = [AREA_STATE_DARK, AREA_STATE_ACCENT, AREA_STATE_SLEEP]

# MagicAreas Components
MAGIC_AREAS_COMPONENTS = [
    BINARY_SENSOR_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    COVER_DOMAIN,
    SWITCH_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
    CLIMATE_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_META = [
    BINARY_SENSOR_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    COVER_DOMAIN,
    SENSOR_DOMAIN,
    LIGHT_DOMAIN,
    CLIMATE_DOMAIN,
]

MAGIC_AREAS_COMPONENTS_GLOBAL = MAGIC_AREAS_COMPONENTS_META

MAGIC_DEVICE_ID_PREFIX = "magic_area_device_"

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

AVAILABLE_ON_STATES = [STATE_ON, STATE_HOME, STATE_PLAYING, STATE_OPEN]

INVALID_STATES = [STATE_UNAVAILABLE, STATE_UNKNOWN]

# Configuration parameters
CONF_ID = "id"
CONF_NAME, DEFAULT_NAME = "name", ""  # cv.string
CONF_TYPE, DEFAULT_TYPE = "type", AREA_TYPE_INTERIOR  # cv.string
CONF_ENABLED_FEATURES, DEFAULT_ENABLED_FEATURES = "features", {}  # cv.ensure_list
CONF_SECONDARY_STATES, DEFAULT_AREA_STATES = "secondary_states", {}  # cv.ensure_list
CONF_INCLUDE_ENTITIES = "include_entities"  # cv.entity_ids
CONF_EXCLUDE_ENTITIES = "exclude_entities"  # cv.entity_ids
(
    CONF_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
) = "presence_device_platforms", [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
]  # cv.ensure_list
ALL_PRESENCE_DEVICE_PLATFORMS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
    REMOTE_DOMAIN,
]
(
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
) = "presence_sensor_device_class", [
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.OCCUPANCY,
    BinarySensorDeviceClass.PRESENCE,
]  # cv.ensure_list
CONF_ON_STATES, DEFAULT_ON_STATES = "on_states", [
    STATE_ON,
    STATE_OPEN,
]  # cv.ensure_list
CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES = (
    "aggregates_min_entities",
    2,
)  # cv.positive_int
CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT = "clear_timeout", 60  # cv.positive_int
CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL = "update_interval", 60  # cv.positive_int
CONF_ICON, DEFAULT_ICON = "icon", "mdi:texture-box"  # cv.string
CONF_NOTIFICATION_DEVICES, DEFAULT_NOTIFICATION_DEVICES = (
    "notification_devices",
    [],
)  # cv.entity_ids
CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES = "notification_states", [
    AREA_STATE_EXTENDED,
]  # cv.ensure_list

# Secondary states options
CONF_DARK_ENTITY = "dark_entity"
CONF_DARK_STATE, DEFAULT_DARK_STATE = "dark_state", STATE_ON
CONF_ACCENT_ENTITY = "accent_entity"
CONF_ACCENT_STATE, DEFAULT_ACCENT_STATE = "accent_state", STATE_ON
CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT = (
    "sleep_timeout",
    DEFAULT_CLEAR_TIMEOUT,
)  # int
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_SLEEP_STATE, DEFAULT_SLEEP_STATE = "sleep_state", STATE_ON
CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME = "extended_time", 120  # cv.positive_int
CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT = "extended_timeout", 300  # int

CONFIGURABLE_AREA_STATE_MAP = {
    AREA_STATE_SLEEP: (CONF_SLEEP_ENTITY, CONF_SLEEP_STATE),
    AREA_STATE_DARK: (CONF_DARK_ENTITY, CONF_DARK_STATE),
    AREA_STATE_ACCENT: (CONF_ACCENT_ENTITY, CONF_ACCENT_STATE),
}

# features
CONF_FEATURE_CLIMATE_GROUPS = "climate_groups"

CONF_FEATURE_MEDIA_PLAYER_GROUPS = "media_player_groups"
CONF_FEATURE_LIGHT_GROUPS = "light_groups"
CONF_FEATURE_COVER_GROUPS = "cover_groups"
CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER = "area_aware_media_player"
CONF_FEATURE_AGGREGATION = "aggregates"
CONF_FEATURE_HEALTH = "health"
CONF_FEATURE_PRESENCE_HOLD = "presence_hold"

CONF_FEATURE_LIST_META = [
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_COVER_GROUPS,
    CONF_FEATURE_CLIMATE_GROUPS,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
]

CONF_FEATURE_LIST = CONF_FEATURE_LIST_META + [
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_PRESENCE_HOLD,
]

CONF_FEATURE_LIST_GLOBAL = CONF_FEATURE_LIST_META

# Presence Hold options
CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT = (
    "presence_hold_timeout",
    0,
)  # cv.int

# Climate Group Options
CONF_CLIMATE_GROUPS_TURN_ON_STATE, DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE = (
    "turn_on_state",
    AREA_STATE_EXTENDED,
)

# Light group options
CONF_OVERHEAD_LIGHTS = "overhead_lights"  # cv.entity_ids
CONF_OVERHEAD_LIGHTS_STATES = "overhead_lights_states"  # cv.ensure_list
CONF_OVERHEAD_LIGHTS_ACT_ON = "overhead_lights_act_on"  # cv.ensure_list
CONF_SLEEP_LIGHTS = "sleep_lights"
CONF_SLEEP_LIGHTS_STATES = "sleep_lights_states"
CONF_SLEEP_LIGHTS_ACT_ON = "sleep_lights_act_on"
CONF_ACCENT_LIGHTS = "accent_lights"
CONF_ACCENT_LIGHTS_STATES = "accent_lights_states"
CONF_ACCENT_LIGHTS_ACT_ON = "accent_lights_act_on"
CONF_TASK_LIGHTS = "task_lights"
CONF_TASK_LIGHTS_STATES = "task_lights_states"
CONF_TASK_LIGHTS_ACT_ON = "task_lights_act_on"

LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE = "occupancy"
LIGHT_GROUP_ACT_ON_STATE_CHANGE = "state"
DEFAULT_LIGHT_GROUP_ACT_ON = [
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
]
LIGHT_GROUP_ACT_ON_OPTIONS = [
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
]

LIGHT_GROUP_DEFAULT_ICON = "mdi:lightbulb-group"

LIGHT_GROUP_ICONS = {
    CONF_OVERHEAD_LIGHTS: "mdi:ceiling-light",
    CONF_SLEEP_LIGHTS: "mdi:sleep",
    CONF_ACCENT_LIGHTS: "mdi:outdoor-lamp",
    CONF_TASK_LIGHTS: "mdi:desk-lamp",
}

LIGHT_GROUP_STATES = {
    CONF_OVERHEAD_LIGHTS: CONF_OVERHEAD_LIGHTS_STATES,
    CONF_SLEEP_LIGHTS: CONF_SLEEP_LIGHTS_STATES,
    CONF_ACCENT_LIGHTS: CONF_ACCENT_LIGHTS_STATES,
    CONF_TASK_LIGHTS: CONF_TASK_LIGHTS_STATES,
}

LIGHT_GROUP_ACT_ON = {
    CONF_OVERHEAD_LIGHTS: CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_SLEEP_LIGHTS: CONF_SLEEP_LIGHTS_ACT_ON,
    CONF_ACCENT_LIGHTS: CONF_ACCENT_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS: CONF_TASK_LIGHTS_ACT_ON,
}

LIGHT_GROUP_CATEGORIES = [
    CONF_OVERHEAD_LIGHTS,
    CONF_SLEEP_LIGHTS,
    CONF_ACCENT_LIGHTS,
    CONF_TASK_LIGHTS,
]

AGGREGATE_BINARY_SENSOR_CLASSES = [
    BinarySensorDeviceClass.WINDOW,
    BinarySensorDeviceClass.DOOR,
    BinarySensorDeviceClass.MOTION,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.LIGHT,
]

AGGREGATE_MODE_ALL = [
    BinarySensorDeviceClass.CONNECTIVITY,
    BinarySensorDeviceClass.PLUG,
]

# Health related
DISTRESS_SENSOR_CLASSES = [
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.GAS,
]  # @todo make configurable
DISTRESS_STATES = [STATE_ALARM_TRIGGERED, STATE_ON, STATE_PROBLEM]

# Aggregates
AGGREGATE_SENSOR_CLASSES = (
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.HUMIDITY,
    SensorDeviceClass.ILLUMINANCE,
    SensorDeviceClass.POWER,
    SensorDeviceClass.TEMPERATURE,
)

AGGREGATE_MODE_SUM = [
    SensorDeviceClass.POWER,
    SensorDeviceClass.CURRENT,
    SensorDeviceClass.ENERGY,
]

# Config Schema

AGGREGATE_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_AGGREGATES_MIN_ENTITIES, default=DEFAULT_AGGREGATES_MIN_ENTITIES
        ): cv.positive_int,
    }
)

PRESENCE_HOLD_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_PRESENCE_HOLD_TIMEOUT, default=DEFAULT_PRESENCE_HOLD_TIMEOUT
        ): cv.positive_int,
    }
)

CLIMATE_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_CLIMATE_GROUPS_TURN_ON_STATE,
            default=DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE,
        ): str,
    }
)

LIGHT_GROUP_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_OVERHEAD_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_STATES, default=[AREA_STATE_OCCUPIED]
        ): cv.ensure_list,
        vol.Optional(
            CONF_OVERHEAD_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_SLEEP_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_SLEEP_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_SLEEP_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_ACCENT_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_ACCENT_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_ACCENT_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
        vol.Optional(CONF_TASK_LIGHTS, default=[]): cv.entity_ids,
        vol.Optional(CONF_TASK_LIGHTS_STATES, default=[]): cv.ensure_list,
        vol.Optional(
            CONF_TASK_LIGHTS_ACT_ON, default=DEFAULT_LIGHT_GROUP_ACT_ON
        ): cv.ensure_list,
    }
)

AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NOTIFICATION_DEVICES, default=[]): cv.entity_ids,
        vol.Optional(CONF_NOTIFY_STATES, default=DEFAULT_NOTIFY_STATES): cv.ensure_list,
    }
)

ALL_FEATURES = set(CONF_FEATURE_LIST) | set(CONF_FEATURE_LIST_GLOBAL)

CONFIGURABLE_FEATURES = {
    CONF_FEATURE_LIGHT_GROUPS: LIGHT_GROUP_FEATURE_SCHEMA,
    CONF_FEATURE_CLIMATE_GROUPS: CLIMATE_GROUP_FEATURE_SCHEMA,
    CONF_FEATURE_AGGREGATION: AGGREGATE_FEATURE_SCHEMA,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
    CONF_FEATURE_PRESENCE_HOLD: PRESENCE_HOLD_FEATURE_SCHEMA,
}

NON_CONFIGURABLE_FEATURES_META = [
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_CLIMATE_GROUPS,
]

NON_CONFIGURABLE_FEATURES = {
    feature: {}
    for feature in ALL_FEATURES
    if feature not in CONFIGURABLE_FEATURES.keys()
}

FEATURES_SCHEMA = vol.Schema(
    {
        vol.Optional(feature): feature_schema
        for feature, feature_schema in chain(
            CONFIGURABLE_FEATURES.items(), NON_CONFIGURABLE_FEATURES.items()
        )
    }
)

SECONDARY_STATES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_SLEEP_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_SLEEP_STATE, default=DEFAULT_SLEEP_STATE): str,
        vol.Optional(
            CONF_SLEEP_TIMEOUT, default=DEFAULT_SLEEP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(CONF_DARK_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_DARK_STATE, default=DEFAULT_DARK_STATE): str,
        vol.Optional(CONF_ACCENT_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_ACCENT_STATE, default=DEFAULT_ACCENT_STATE): str,
        vol.Optional(
            CONF_EXTENDED_TIME, default=DEFAULT_EXTENDED_TIME
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIMEOUT, default=DEFAULT_EXTENDED_TIMEOUT
        ): cv.positive_int,
    }
)

# Magic Areas
REGULAR_AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): vol.In(
            [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]
        ),
        vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_PRESENCE_DEVICE_PLATFORMS,
            default=DEFAULT_PRESENCE_DEVICE_PLATFORMS,
        ): cv.ensure_list,
        vol.Optional(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS,
            default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        ): cv.ensure_list,
        vol.Optional(CONF_ON_STATES, default=DEFAULT_ON_STATES): cv.ensure_list,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_SECONDARY_STATES, default={}): SECONDARY_STATES_SCHEMA,
    }
)

META_AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=AREA_TYPE_META): AREA_TYPE_META,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_ON_STATES, default=DEFAULT_ON_STATES): cv.ensure_list,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
        vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    }
)

AREA_SCHEMA = vol.Schema(vol.Any(REGULAR_AREA_SCHEMA, META_AREA_SCHEMA))

_DOMAIN_SCHEMA = vol.Schema({cv.slug: vol.Any(AREA_SCHEMA, None)})

# VALIDATION_TUPLES
OPTIONS_AREA = [
    (CONF_TYPE, DEFAULT_TYPE, vol.In([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR])),
    (CONF_INCLUDE_ENTITIES, [], cv.entity_ids),
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
    (
        CONF_PRESENCE_DEVICE_PLATFORMS,
        DEFAULT_PRESENCE_DEVICE_PLATFORMS,
        cv.ensure_list,
    ),
    (
        CONF_PRESENCE_SENSOR_DEVICE_CLASS,
        DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        cv.ensure_list,
    ),
    (
        CONF_ON_STATES,
        DEFAULT_ON_STATES,
        cv.ensure_list,
    ),
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
    (CONF_ICON, DEFAULT_ICON, str),
]

OPTIONS_AREA_META = [
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
    (CONF_ICON, DEFAULT_ICON, str),
]

OPTIONS_SECONDARY_STATES = [
    (CONF_SLEEP_ENTITY, "", cv.entity_id),
    (CONF_SLEEP_STATE, DEFAULT_SLEEP_STATE, str),
    (CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT, int),
    (CONF_DARK_ENTITY, "", cv.entity_id),
    (CONF_DARK_STATE, DEFAULT_DARK_STATE, str),
    (CONF_ACCENT_ENTITY, "", cv.entity_id),
    (CONF_ACCENT_STATE, DEFAULT_ACCENT_STATE, str),
    (CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME, int),
    (CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT, int),
]

OPTIONS_LIGHT_GROUP = [
    (CONF_OVERHEAD_LIGHTS, [], cv.entity_ids),
    (CONF_OVERHEAD_LIGHTS_STATES, [AREA_STATE_OCCUPIED], cv.ensure_list),
    (CONF_OVERHEAD_LIGHTS_ACT_ON, DEFAULT_LIGHT_GROUP_ACT_ON, cv.ensure_list),
    (CONF_SLEEP_LIGHTS, [], cv.entity_ids),
    (CONF_SLEEP_LIGHTS_STATES, [], cv.ensure_list),
    (CONF_SLEEP_LIGHTS_ACT_ON, DEFAULT_LIGHT_GROUP_ACT_ON, cv.ensure_list),
    (CONF_ACCENT_LIGHTS, [], cv.entity_ids),
    (CONF_ACCENT_LIGHTS_STATES, [], cv.ensure_list),
    (CONF_ACCENT_LIGHTS_ACT_ON, DEFAULT_LIGHT_GROUP_ACT_ON, cv.ensure_list),
    (CONF_TASK_LIGHTS, [], cv.entity_ids),
    (CONF_TASK_LIGHTS_STATES, [], cv.ensure_list),
    (CONF_TASK_LIGHTS_ACT_ON, DEFAULT_LIGHT_GROUP_ACT_ON, cv.ensure_list),
]

OPTIONS_AGGREGATES = [
    (CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES, int),
]

OPTIONS_PRESENCE_HOLD = [
    (CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT, int),
]

OPTIONS_CLIMATE_GROUP = [
    (CONF_CLIMATE_GROUPS_TURN_ON_STATE, DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE, str),
]

OPTIONS_CLIMATE_GROUP_META = [
    (CONF_CLIMATE_GROUPS_TURN_ON_STATE, None, str),
]

OPTIONS_AREA_AWARE_MEDIA_PLAYER = [
    (CONF_NOTIFICATION_DEVICES, [], cv.entity_ids),
    (CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES, cv.ensure_list),
]

# Config Flow filters
CONFIG_FLOW_ENTITY_FILTER = [
    BINARY_SENSOR_DOMAIN,
    SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    INPUT_BOOLEAN_DOMAIN,
]
CONFIG_FLOW_ENTITY_FILTER_EXT = CONFIG_FLOW_ENTITY_FILTER + [
    LIGHT_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    CLIMATE_DOMAIN,
    SUN_DOMAIN,
]
