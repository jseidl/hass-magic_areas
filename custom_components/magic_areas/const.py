"""Constants for Magic Areas."""

from enum import IntEnum, StrEnum
from itertools import chain

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.device_tracker.const import (
    DOMAIN as DEVICE_TRACKER_DOMAIN,
)
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.sun import DOMAIN as SUN_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    STATE_ALARM_TRIGGERED,
    STATE_ON,
    STATE_OPEN,
    STATE_PLAYING,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import config_validation as cv

ONE_MINUTE = 60  # seconds, for conversion

DOMAIN = "magic_areas"
MODULE_DATA = f"{DOMAIN}_data"

ADDITIONAL_LIGHT_TRACKING_ENTITIES = ["sun.sun"]
DEFAULT_SENSOR_PRECISION = 2

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


class LightGroupCategory(StrEnum):
    """Categories of light groups."""

    ALL = "all_lights"
    OVERHEAD = "overhead_lights"
    TASK = "task_lights"
    ACCENT = "accent_lights"
    SLEEP = "sleep_lights"


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

AGGREGATE_MODE_TOTAL_SENSOR = [
    SensorDeviceClass.ENERGY,
]


class MagicConfigEntryVersion(IntEnum):
    """Magic Area config entry version."""

    MAJOR = 2
    MINOR = 1


class MagicAreasFeatureInfo:
    """Base class for feature information."""

    id: str
    translation_keys: dict[str, str]
    icons: dict[str, str] = {}


class MagicAreasFeatureInfoPresenceTracking(MagicAreasFeatureInfo):
    """Feature information for feature: Presence Tracking."""

    id = "presence_tracking"
    translation_keys = {BINARY_SENSOR_DOMAIN: "area_state"}


class MagicAreasFeatureInfoPresenceHold(MagicAreasFeatureInfo):
    """Feature information for feature: Presence hold."""

    id = "presence_hold"
    translation_keys = {SWITCH_DOMAIN: "presence_hold"}
    icons = {SWITCH_DOMAIN: "mdi:car-brake-hold"}


class MagicAreasFeatureInfoAggregates(MagicAreasFeatureInfo):
    """Feature information for feature: Aggregates."""

    id = "aggregates"
    translation_keys = {
        BINARY_SENSOR_DOMAIN: "aggregate",
        SENSOR_DOMAIN: "aggregate",
    }


class MagicAreasFeatureInfoThrehsold(MagicAreasFeatureInfo):
    """Feature information for feature: Aggregate Threshold Sensors."""

    id = "threshold"
    translation_keys = {BINARY_SENSOR_DOMAIN: "threshold"}


class MagicAreasFeatureInfoHealth(MagicAreasFeatureInfo):
    """Feature information for feature: Health sensors."""

    id = "health"
    translation_keys = {BINARY_SENSOR_DOMAIN: "health"}


class MagicAreasFeatureInfoLightGroups(MagicAreasFeatureInfo):
    """Feature information for feature: Light groups."""

    id = "light_groups"
    translation_keys = {
        LIGHT_DOMAIN: None,  # let light category be appended to it
        SWITCH_DOMAIN: "light_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:lightbulb-auto-outline"}


class MagicAreasFeatureInfoClimateGroups(MagicAreasFeatureInfo):
    """Feature information for feature: Climate groups."""

    id = "climate_groups"
    translation_keys = {
        CLIMATE_DOMAIN: "climate_group",
        SWITCH_DOMAIN: "climate_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:thermostat-auto"}


class MagicAreasFeatureInfoMediaPlayerGroups(MagicAreasFeatureInfo):
    """Feature information for feature: Media player groups."""

    id = "media_player_groups"
    translation_keys = {
        MEDIA_PLAYER_DOMAIN: "media_player_group",
        SWITCH_DOMAIN: "media_player_control",
    }
    icons = {SWITCH_DOMAIN: "mdi:auto-mode"}


class MagicAreasFeatureInfoCoverGroups(MagicAreasFeatureInfo):
    """Feature information for feature: Cover groups."""

    id = "cover_groups"
    translation_keys = {COVER_DOMAIN: "cover_group"}


class MagicAreasFeatureInfoAreaAwareMediaPlayer(MagicAreasFeatureInfo):
    """Feature information for feature: Area-aware media player."""

    id = "area_aware_media_player"
    translation_keys = {MEDIA_PLAYER_DOMAIN: "area_aware_media_player"}


class MagicAreasFeatures(StrEnum):
    """Magic Areas features."""

    AREA = "area"  # Default feature
    PRESENCE_HOLD = "presence_hold"
    LIGHT_GROUPS = "light_groups"
    CLIMATE_GROUPS = "climate_groups"
    COVER_GROUPS = "cover_groups"
    MEDIA_PLAYER_GROUPS = "media_player_groups"
    AREA_AWARE_MEDIA_PLAYER = "area_aware_media_player"
    AGGREGATES = "aggregates"
    HEALTH = "health"
    THRESHOLD = "threshold"


# Magic Areas Events
class MagicAreasEvents(StrEnum):
    """Magic Areas events."""

    STARTED = "magicareas_start"
    READY = "magicareas_ready"
    AREA_READY = "magicareas_area_ready"
    AREA_STATE_CHANGED = "magicareas_area_state_changed"


EVENT_MAGICAREAS_STARTED = "magicareas_start"
EVENT_MAGICAREAS_READY = "magicareas_ready"
EVENT_MAGICAREAS_AREA_READY = "magicareas_area_ready"
EVENT_MAGICAREAS_AREA_OCCUPIED = "magicareas_area_occupied"
EVENT_MAGICAREAS_AREA_CLEAR = "magicareas_area_clear"
EVENT_MAGICAREAS_AREA_STATE_CHANGED = "magicareas_area_state_changed"

ALL_BINARY_SENSOR_DEVICE_CLASSES = [cls.value for cls in BinarySensorDeviceClass]
ALL_SENSOR_DEVICE_CLASSES = [cls.value for cls in SensorDeviceClass]

# Data Items
DATA_AREA_OBJECT = "area_object"
DATA_UNDO_UPDATE_LISTENER = "undo_update_listener"

# Attributes
ATTR_STATES = "states"
ATTR_AREAS = "areas"
ATTR_ACTIVE_AREAS = "active_areas"
ATTR_TYPE = "type"
ATTR_UPDATE_INTERVAL = "update_interval"
ATTR_CLEAR_TIMEOUT = "clear_timeout"
ATTR_ACTIVE_SENSORS = "active_sensors"
ATTR_LAST_ACTIVE_SENSORS = "last_active_sensors"
ATTR_FEATURES = "features"
ATTR_PRESENCE_SENSORS = "presence_sensors"

PRESENCE_SENSOR_VALID_ON_STATES = [STATE_ON, STATE_OPEN, STATE_PLAYING]

# Icons
ICON_PRESENCE_HOLD = "mdi:car-brake-hold"
ICON_LIGHT_CONTROL = "mdi:lightbulb-auto-outline"


class MetaAreaIcons(StrEnum):
    """Meta area icons."""

    INTERIOR = "mdi:home-import-outline"
    EXTERIOR = "mdi:home-export-outline"
    GLOBAL = "mdi:home"


class FeatureIcons(StrEnum):
    """Feature related icons."""

    PRESENCE_HOLD_SWITCH = "mdi:car-brake-hold"
    LIGHT_CONTROL_SWITCH = "mdi:lightbulb-auto-outline"
    MEDIA_CONTROL_SWITCH = "mdi:auto-mode"
    CLIMATE_CONTROL_SWITCH = "mdi:thermostat-auto"


class AreaStates(StrEnum):
    """Magic area states."""

    CLEAR = "clear"
    OCCUPIED = "occupied"
    EXTENDED = "extended"
    DARK = "dark"
    BRIGHT = "bright"
    SLEEP = "sleep"
    ACCENT = "accented"


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

MAGICAREAS_UNIQUEID_PREFIX = "magic_areas"
MAGIC_DEVICE_ID_PREFIX = "magic_area_device_"


class AreaType(StrEnum):
    """Regular area types."""

    INTERIOR = "interior"
    EXTERIOR = "exterior"
    META = "meta"


# Meta Areas
class MetaAreaType(StrEnum):
    """Meta area types."""

    GLOBAL = "global"
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FLOOR = "floor"


META_AREA_GLOBAL = "Global"
META_AREA_INTERIOR = "Interior"
META_AREA_EXTERIOR = "Exterior"
META_AREAS = [META_AREA_GLOBAL, META_AREA_INTERIOR, META_AREA_EXTERIOR]

# Area Types
AREA_TYPE_META = "meta"
AREA_TYPE_INTERIOR = "interior"
AREA_TYPE_EXTERIOR = "exterior"
AREA_TYPES = [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR, AREA_TYPE_META]

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
) = (
    "presence_device_platforms",
    [
        MEDIA_PLAYER_DOMAIN,
        BINARY_SENSOR_DOMAIN,
    ],
)  # cv.ensure_list
ALL_PRESENCE_DEVICE_PLATFORMS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
    REMOTE_DOMAIN,
    DEVICE_TRACKER_DOMAIN,
]
(
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
) = (
    "presence_sensor_device_class",
    [
        BinarySensorDeviceClass.MOTION,
        BinarySensorDeviceClass.OCCUPANCY,
        BinarySensorDeviceClass.PRESENCE,
    ],
)  # cv.ensure_list
CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES = (
    "aggregates_min_entities",
    2,
)  # cv.positive_int
(
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
) = (
    "aggregates_binary_sensor_device_classes",
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
)  # cv.ensure_list
CONF_AGGREGATES_SENSOR_DEVICE_CLASSES, DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES = (
    "aggregates_sensor_device_classes",
    ALL_SENSOR_DEVICE_CLASSES,
)  # cv.ensure_list
CONF_AGGREGATES_ILLUMINANCE_THRESHOLD, DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD = (
    "aggregates_illuminance_threshold",
    0,  # 0 = disabled
)  # cv.positive_int

CONF_HEALTH_SENSOR_DEVICE_CLASSES, DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES = (
    "health_binary_sensor_device_classes",
    DISTRESS_SENSOR_CLASSES,
)

CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT_META = (
    "clear_timeout",
    1,
    0,
)  # cv.positive_int
CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL = "update_interval", 60  # cv.positive_int
CONF_NOTIFICATION_DEVICES, DEFAULT_NOTIFICATION_DEVICES = (
    "notification_devices",
    [],
)  # cv.entity_ids
CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES = (
    "notification_states",
    [
        AREA_STATE_EXTENDED,
    ],
)  # cv.ensure_list

# Secondary states options
CONF_DARK_ENTITY = "dark_entity"
CONF_ACCENT_ENTITY = "accent_entity"
CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT = (
    "sleep_timeout",
    DEFAULT_CLEAR_TIMEOUT,
)  # int
CONF_SLEEP_ENTITY = "sleep_entity"
CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME = "extended_time", 5  # cv.positive_int
CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT = "extended_timeout", 10  # int

CONFIGURABLE_AREA_STATE_MAP = {
    AREA_STATE_SLEEP: CONF_SLEEP_ENTITY,
    AREA_STATE_DARK: CONF_DARK_ENTITY,
    AREA_STATE_ACCENT: CONF_ACCENT_ENTITY,
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


# Config Schema

AGGREGATE_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_AGGREGATES_MIN_ENTITIES, default=DEFAULT_AGGREGATES_MIN_ENTITIES
        ): cv.positive_int,
        vol.Optional(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
        vol.Optional(
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
            default=DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
        ): cv.positive_int,
    }
)

HEALTH_FEATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_HEALTH_SENSOR_DEVICE_CLASSES,
            default=DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        ): cv.ensure_list,
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
    CONF_FEATURE_HEALTH: HEALTH_FEATURE_SCHEMA,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER: AREA_AWARE_MEDIA_PLAYER_FEATURE_SCHEMA,
    CONF_FEATURE_PRESENCE_HOLD: PRESENCE_HOLD_FEATURE_SCHEMA,
}

NON_CONFIGURABLE_FEATURES_META = [
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_CLIMATE_GROUPS,
]

NON_CONFIGURABLE_FEATURES = {
    feature: {} for feature in ALL_FEATURES if feature not in CONFIGURABLE_FEATURES
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
        vol.Optional(CONF_DARK_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_ACCENT_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(CONF_SLEEP_ENTITY, default=""): vol.Any("", cv.entity_id),
        vol.Optional(
            CONF_SLEEP_TIMEOUT, default=DEFAULT_SLEEP_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIME, default=DEFAULT_EXTENDED_TIME
        ): cv.positive_int,
        vol.Optional(
            CONF_EXTENDED_TIMEOUT, default=DEFAULT_EXTENDED_TIMEOUT
        ): cv.positive_int,
    }
)

# Basic Area Options Schema
REGULAR_AREA_BASIC_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=DEFAULT_TYPE): vol.In(
            [AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR]
        ),
        vol.Optional(CONF_INCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
    }
)
META_AREA_BASIC_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=AREA_TYPE_META): AREA_TYPE_META,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
    }
)

# Presence Tracking Schema
REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_PRESENCE_DEVICE_PLATFORMS,
            default=DEFAULT_PRESENCE_DEVICE_PLATFORMS,
        ): cv.ensure_list,
        vol.Optional(
            CONF_PRESENCE_SENSOR_DEVICE_CLASS,
            default=DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
        ): cv.ensure_list,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
    }
)

META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT_META
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
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
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_SECONDARY_STATES, default={}): SECONDARY_STATES_SCHEMA,
    }
)

META_AREA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TYPE, default=AREA_TYPE_META): AREA_TYPE_META,
        vol.Optional(CONF_ENABLED_FEATURES, default={}): FEATURES_SCHEMA,
        vol.Optional(CONF_EXCLUDE_ENTITIES, default=[]): cv.entity_ids,
        vol.Optional(
            CONF_CLEAR_TIMEOUT, default=DEFAULT_CLEAR_TIMEOUT_META
        ): cv.positive_int,
        vol.Optional(
            CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
        ): cv.positive_int,
    }
)

AREA_SCHEMA = vol.Schema(vol.Any(REGULAR_AREA_SCHEMA, META_AREA_SCHEMA))

_DOMAIN_SCHEMA = vol.Schema({cv.slug: vol.Any(AREA_SCHEMA, None)})

# VALIDATION_TUPLES
OPTIONS_AREA = [
    (CONF_TYPE, DEFAULT_TYPE, vol.In([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR])),
    (CONF_INCLUDE_ENTITIES, [], cv.entity_ids),
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
]
OPTIONS_PRESENCE_TRACKING = [
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
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
]

OPTIONS_AREA_META = [
    (CONF_EXCLUDE_ENTITIES, [], cv.entity_ids),
]
OPTIONS_PRESENCE_TRACKING_META = [
    (CONF_CLEAR_TIMEOUT, DEFAULT_CLEAR_TIMEOUT, int),
    (CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, int),
]

OPTIONS_SECONDARY_STATES = [
    (CONF_DARK_ENTITY, "", cv.entity_id),
    (CONF_ACCENT_ENTITY, "", cv.entity_id),
    (CONF_SLEEP_ENTITY, "", cv.entity_id),
    (CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT, int),
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
    (
        CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        cv.ensure_list,
    ),
    (
        CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
        DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        cv.ensure_list,
    ),
    (
        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
        DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
        int,
    ),
]

OPTIONS_HEALTH_SENSOR = [
    (
        CONF_HEALTH_SENSOR_DEVICE_CLASSES,
        DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
        cv.ensure_list,
    ),
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
CONFIG_FLOW_ENTITY_FILTER_BOOL = [
    BINARY_SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    INPUT_BOOLEAN_DOMAIN,
]
CONFIG_FLOW_ENTITY_FILTER_EXT = CONFIG_FLOW_ENTITY_FILTER + [
    LIGHT_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    CLIMATE_DOMAIN,
    SUN_DOMAIN,
]
