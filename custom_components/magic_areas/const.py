from dataclasses import dataclass
from enum import StrEnum
from itertools import chain

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
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
ATTR_STATE = "state"
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
ATTR_BRIGHTNESS_PCT = "brightness_pct"

# Icons
ICON_PRESENCE_HOLD = "mdi:car-brake-hold"
ICON_LIGHT_CONTROL = "mdi:lightbulb-auto-outline"


# Area States
class AreaState(StrEnum):
    """The states the area can be in."""

    AREA_STATE_CLEAR = "clear"  # Clear state, not occupied.
    AREA_STATE_OCCUPIED = "occupied"  # main occupied state
    AREA_STATE_EXTENDED = "extended"  # Timeout after main occupied
    AREA_STATE_BRIGHT = "bright"  # Bright state, high lumens
    AREA_STATE_SLEEP = "sleep"  # Sleep state (night)


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
ILLUMINANCE_DEVICE_PLATFORMS = [
    SENSOR_DOMAIN,
]
(
    CONF_ILLUMINANCE_DEVICE_CLASS,
    DEFAULT_ILLUMINANCE_DEVICE_SENSOR_CLASS,
) = (
    "illuminance_sensor_device_class",
    [
        SensorDeviceClass.ILLUMINANCE,
    ],
)  # cv.ensure_list
CONF_ON_STATES, DEFAULT_ON_STATES = (
    "on_states",
    [
        STATE_ON,
        STATE_OPEN,
    ],
)  # cv.ensure_list
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
CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES = (
    "notification_states",
    [
        AreaState.AREA_STATE_EXTENDED,
    ],
)  # cv.ensure_list


# Secondary states options
@dataclass
class LightEntityConf:
    """LightEntityConf configures how the light setups are used in the group."""

    name: str
    default_state: AreaState
    default_dim_level: int
    enable_state: list[AreaState]
    icon: str
    has_entity: bool
    timeout: int

    def entity_name(self):
        """Return the name of the entity to lookup."""
        return self.name + "_entity"

    def state_name(self):
        """Return the name of the state to save in the config."""
        return self.name + "_state"

    def state_timeout(self):
        """Return the name in the state to lookup the timeout."""
        return self.name + "_state_timeout"

    def state_dim_level(self):
        """Return the name in the state to lookup the dim level."""
        return self.name + "_state_dim"

    def act_on(self):
        """Return the name in the state to lookup the act on type."""
        return self.name + "_lights_act_on"

    def lights_name(self):
        """Return the name of the entity to create."""
        return self.name + "_lights"

    def lights_state_name(self):
        """Return the state name of the light group."""
        return self.name + "_lights_state"

    def config_setup(self):
        """Return the config setup for the main section allowing it to be enabled."""
        return {
            vol.Optional(self.lights_name(), default=[]): cv.entity_ids,
            vol.Optional(
                self.state_name(),
                default=self.enable_state,
            ): cv.ensure_list,
            vol.Optional(self.entity_name(), default=[]): cv.entity_ids,
        }

    def main_config_enties(self):
        """Return the config for the main section with the timeouts and name bits."""
        return {
            vol.Optional(self.entity_name(), default=""): vol.Any("", cv.entity_id),
            vol.Optional(self.state_timeout(), default=self.timeout): cv.positive_int,
            vol.Optional(
                self.state_dim_level(), default=self.default_dim_level
            ): cv.positive_int,
        }


# Setups to control all the lights, items to create
brightLights = LightEntityConf(
    name="bright",
    default_state=STATE_ON,
    default_dim_level=0,
    enable_state=AreaState.AREA_STATE_BRIGHT,
    icon="mdi:ceiling-light",
    has_entity=True,
    timeout=120,
)
sleepLights = LightEntityConf(
    name="sleep",
    default_state=STATE_ON,
    default_dim_level=30,
    enable_state=AreaState.AREA_STATE_SLEEP,
    icon="mdi:sleep",
    has_entity=True,
    timeout=120,
)
occupiedLights = LightEntityConf(
    name="occupied",
    default_state=STATE_ON,
    default_dim_level=30,
    enable_state=AreaState.AREA_STATE_OCCUPIED,
    icon="mdi:desk-lamp",
    timeout=1800,
    has_entity=False,
)
extendedLights = LightEntityConf(
    name="extended",
    default_state=STATE_ON,
    default_dim_level=0,
    enable_state=AreaState.AREA_STATE_EXTENDED,
    timeout=120,
    has_entity=False,
    icon="mdi:desk-lamp",
)

# All the light setup pieces.
ALL_LIGHT_ENTITIES = [sleepLights, brightLights, extendedLights, occupiedLights]

# features
CONF_FEATURE_CLIMATE_GROUPS = "climate_groups"
CONF_FEATURE_IMMUMINANCE_GROUPS = "illuminance_groups"
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

CONF_FEATURE_LIST = [
    *CONF_FEATURE_LIST_META,
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

LIGHT_GROUP_DEFAULT_ICON = "mdi:lightbulb-group"

LIGHT_GROUP_ICONS = {}


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

LIGHT_GROUP_FEATURE_SCHEMA = vol.Schema({})
for l_g in ALL_LIGHT_ENTITIES:
    LIGHT_GROUP_FEATURE_SCHEMA = LIGHT_GROUP_FEATURE_SCHEMA.extend(l_g.config_setup())


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

SECONDARY_STATES_SCHEMA = vol.Schema({})
for l_g in ALL_LIGHT_ENTITIES:
    SECONDARY_STATES_SCHEMA = SECONDARY_STATES_SCHEMA.extend(l_g.main_config_enties())

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
CONFIG_FLOW_ENTITY_FILTER_EXT = [
    *CONFIG_FLOW_ENTITY_FILTER,
    LIGHT_DOMAIN,
    MEDIA_PLAYER_DOMAIN,
    CLIMATE_DOMAIN,
    SUN_DOMAIN,
]
