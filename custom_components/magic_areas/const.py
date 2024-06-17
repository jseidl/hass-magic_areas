"""Constants for Magic Areas."""

from enum import IntEnum, StrEnum

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
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
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

from .base.config import MagicAreasConfigOption, MagicAreasConfigOptionSet


# Enums
class MagicAreasDataKey(StrEnum):
    """Keys for the hass.data dictionary."""

    MODULE_DATA = "magicareas"
    AREA = "area"
    TRACKER = "state_tracker"
    TRACKED_LISTENERS = "tracked_listeners"


class AreaState(StrEnum):
    """Magic area states."""

    CLEAR = "clear"
    OCCUPIED = "occupied"
    EXTENDED = "extended"
    DARK = "dark"
    BRIGHT = "bright"
    SLEEP = "sleep"
    ACCENT = "accented"


class AreaType(StrEnum):
    """Regular area types."""

    INTERIOR = "interior"
    EXTERIOR = "exterior"
    META = "meta"


class MetaAreaType(StrEnum):
    """Meta area types."""

    GLOBAL = "global"
    INTERIOR = "interior"
    EXTERIOR = "exterior"
    FLOOR = "floor"


class MetaAreaIcons(StrEnum):
    """Meta area icons."""

    INTERIOR = "mdi:home-import-outline"
    EXTERIOR = "mdi:home-export-outline"
    GLOBAL = "mdi:home"


class MagicAreasEvent(StrEnum):
    """Magic Areas events."""

    STARTED = "magicareas_start"
    READY = "magicareas_ready"
    AREA_READY = "magicareas_area_ready"
    AREA_STATE_CHANGED = "magicareas_area_state_changed"


class LightGroupCategory(StrEnum):
    """Categories of light groups."""

    ALL = "all_lights"
    OVERHEAD = "overhead_lights"
    TASK = "task_lights"
    ACCENT = "accent_lights"
    SLEEP = "sleep_lights"


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


class AreaEventType(StrEnum):
    """Type of events an area can have."""

    OCCUPANCY = "occupancy"
    STATE = "state"


class MagicAreasPrefix(StrEnum):
    """Prefix for ID generation."""

    UNIQUE_ID = "magic_areas"
    DEVICE_ID = "magic_area_device"


class CustomAttribute(StrEnum):
    """Custom attributes for entities."""

    STATES = "states"
    AREAS = "areas"
    AREA_TYPE = "type"
    UPDATE_INTERVAL = "update_interval"
    CLEAR_TIMEOUT = "clear_timeout"
    ACTIVE_SENSORS = "active_sensors"
    LAST_ACTIVE_SENSORS = "last_active_sensors"
    FEATURES = "features"
    PRESENCE_SENSORS = "presence_sensors"


class OptionSetKey(StrEnum):
    """Keys for OptionSets."""

    AREA_INFO = "area_info"
    AREA_HEALTH = "area_health"
    AGGREGATES = "aggregates"
    PRESENCE_HOLD = "presence_hold"
    CLIMATE_GROUPS = "climate_groups"
    LIGHT_GROUPS = "light_groups"
    AREA_AWARE_MEDIA_PLAYER = "area_aware_media_player"
    SECONDARY_STATES = "secondary_states"


# General
DOMAIN = "magic_areas"

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

ADDITIONAL_LIGHT_TRACKING_ENTITIES = ["sun.sun"]

# Shortcuts
EMPTY_STR = ""
ONE_MINUTE = 60  # seconds, for conversion
ALL_BINARY_SENSOR_DEVICE_CLASSES = [cls.value for cls in BinarySensorDeviceClass]
ALL_SENSOR_DEVICE_CLASSES = [cls.value for cls in SensorDeviceClass]
INVALID_STATES = [STATE_UNAVAILABLE, STATE_UNKNOWN]
PRESENCE_SENSOR_VALID_ON_STATES = [STATE_ON, STATE_OPEN, STATE_PLAYING]
LIGHT_CONTROL_AREA_STATES = [
    AreaState.OCCUPIED,
    AreaState.EXTENDED,
    AreaState.ACCENT,
    AreaState.SLEEP,
]
DISTRESS_SENSOR_CLASSES = [
    BinarySensorDeviceClass.PROBLEM,
    BinarySensorDeviceClass.SMOKE,
    BinarySensorDeviceClass.MOISTURE,
    BinarySensorDeviceClass.SAFETY,
    BinarySensorDeviceClass.GAS,
]
DISTRESS_STATES = [STATE_ALARM_TRIGGERED, STATE_ON, STATE_PROBLEM]


class AreaStateGroups:
    """Shortcut class for groups of area states."""

    exclusive: list[str] = [AreaState.SLEEP, AreaState.ACCENT]
    builtin: list[str] = [AreaState.OCCUPIED, AreaState.EXTENDED]
    configurable: list[str] = [AreaState.DARK, AreaState.ACCENT, AreaState.SLEEP]


# Options
class MagicConfigEntryVersion(IntEnum):
    """Magic Area config entry version."""

    MAJOR = 2
    MINOR = 1


## Basic Area Info
class AreaInfoOptionKey(StrEnum):
    """Option keys for area info option set."""

    TYPE = "type"
    INCLUDE_ENTITIES = "include_entities"
    EXCLUDE_ENTITIES = "exclude_entities"
    PRESENCE_SENSOR_DOMAINS = "presence_sensor_domains"
    PRESENCE_SENSOR_DEVICE_CLASSES = "presence_sensor_device_class"
    CLEAR_TIMEOUT = "clear_timeout"
    UPDATE_INTERVAL = "update_interval"


class AreaInfoOptionSet(MagicAreasConfigOptionSet):
    """Area info option set."""

    key = OptionSetKey.AREA_INFO
    options = [
        MagicAreasConfigOption(
            AreaInfoOptionKey.TYPE,
            validator=vol.In,
            default=AreaType.INTERIOR,
            options=[AreaType.INTERIOR, AreaType.EXTERIOR],
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.INCLUDE_ENTITIES, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.EXCLUDE_ENTITIES, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.PRESENCE_SENSOR_DOMAINS,
            validator=cv.ensure_list,
            default=[BINARY_SENSOR_DOMAIN, MEDIA_PLAYER_DOMAIN],
            options=[
                BINARY_SENSOR_DOMAIN,
                MEDIA_PLAYER_DOMAIN,
                DEVICE_TRACKER_DOMAIN,
                REMOTE_DOMAIN,
            ],
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.PRESENCE_SENSOR_DEVICE_CLASSES,
            validator=cv.ensure_list,
            default=[
                BinarySensorDeviceClass.MOTION,
                BinarySensorDeviceClass.OCCUPANCY,
                BinarySensorDeviceClass.PRESENCE,
            ],
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.CLEAR_TIMEOUT, validator=cv.positive_int, default=1
        ),
        MagicAreasConfigOption(
            AreaInfoOptionKey.UPDATE_INTERVAL, validator=cv.positive_int, default=60
        ),
    ]


class SecondaryStatesOptionKey(StrEnum):
    """Option keys for secondary states option set."""

    AREA_LIGHT_SENSOR = "dark_entity"
    ACCENT_ENTITY = "accent_entity"
    SLEEP_ENTITY = "sleep_entity"
    SLEEP_TIMEOUT = "sleep_timeout"
    EXTENDED_TIME = "extended_time"
    EXTENDED_TIMEOUT = "extended_timeout"


class SecondaryStatesOptionSet(MagicAreasConfigOptionSet):
    """Secondary states option set."""

    key = OptionSetKey.SECONDARY_STATES
    options = [
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.AREA_LIGHT_SENSOR, [EMPTY_STR, cv.entity_id]
        ),
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.ACCENT_ENTITY, [EMPTY_STR, cv.entity_id]
        ),
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.SLEEP_ENTITY, [EMPTY_STR, cv.entity_id]
        ),
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.SLEEP_TIMEOUT,
            validator=cv.positive_int,
            default=15,
        ),
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.EXTENDED_TIME, validator=cv.positive_int, default=5
        ),
        MagicAreasConfigOption(
            SecondaryStatesOptionKey.EXTENDED_TIMEOUT,
            validator=cv.positive_int,
            default=5,
        ),
    ]


class LightGroupOptionKey(StrEnum):
    """Option keys for light groups option set."""

    OVERHEAD_LIGHTS = "overhead_lights"
    OVERHEAD_LIGHTS_STATES = "overhead_lights_states"
    OVERHEAD_LIGHTS_CONTROL_ON = "overhead_lights_act_on"
    SLEEP_LIGHTS = "sleep_lights"
    SLEEP_LIGHTS_STATES = "sleep_lights_states"
    SLEEP_LIGHTS_CONTROL_ON = "sleep_lights_act_on"
    ACCENT_LIGHTS = "accent_lights"
    ACCENT_LIGHTS_STATES = "accent_lights_states"
    ACCENT_LIGHTS_CONTROL_ON = "accent_lights_act_on"
    TASK_LIGHTS = "task_lights"
    TASK_LIGHTS_STATES = "task_lights_states"
    TASK_LIGHTS_CONTROL_ON = "task_lights_act_on"


class LightGroupOptionSet(MagicAreasConfigOptionSet):
    """Light groups option set."""

    key = OptionSetKey.LIGHT_GROUPS
    options = [
        MagicAreasConfigOption(
            LightGroupOptionKey.OVERHEAD_LIGHTS, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.OVERHEAD_LIGHTS_STATES,
            validator=cv.ensure_list,
            default=[AreaState.OCCUPIED],
            options=LIGHT_CONTROL_AREA_STATES,
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.OVERHEAD_LIGHTS_CONTROL_ON,
            validator=cv.ensure_list,
            default=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
            options=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.SLEEP_LIGHTS, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.SLEEP_LIGHTS_STATES,
            validator=cv.ensure_list,
            default=[],
            options=LIGHT_CONTROL_AREA_STATES,
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.SLEEP_LIGHTS_CONTROL_ON,
            validator=cv.ensure_list,
            default=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
            options=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.ACCENT_LIGHTS, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.ACCENT_LIGHTS_STATES,
            validator=cv.ensure_list,
            default=[],
            options=LIGHT_CONTROL_AREA_STATES,
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.ACCENT_LIGHTS_CONTROL_ON,
            validator=cv.ensure_list,
            default=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
            options=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.TASK_LIGHTS, validator=cv.entity_ids, default=[]
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.TASK_LIGHTS_STATES,
            validator=cv.ensure_list,
            default=[],
            options=LIGHT_CONTROL_AREA_STATES,
        ),
        MagicAreasConfigOption(
            LightGroupOptionKey.TASK_LIGHTS_CONTROL_ON,
            validator=cv.ensure_list,
            default=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
            options=[AreaEventType.OCCUPANCY, AreaEventType.STATE],
        ),
    ]


class ClimateGroupOptionKey(StrEnum):
    """Option keys for climate groups option set."""

    TURN_ON_STATE = "turn_on_state"


class ClimateGroupOptionSet(MagicAreasConfigOptionSet):
    """Climate groups option set."""

    key = OptionSetKey.CLIMATE_GROUPS
    options = [
        MagicAreasConfigOption(
            ClimateGroupOptionKey.TURN_ON_STATE,
            validator=str,
            default=AreaState.EXTENDED,
        )
    ]


class AreaAwareMediaPlayerOptionKey(StrEnum):
    """Option keys for area-aware media player option set."""

    NOTIFICATION_DEVICES = "notification_devices"
    NOTIFY_STATES = "notification_states"


class AreaAwareMediaPlayerOptionSet(MagicAreasConfigOptionSet):
    """Area-aware media player option set."""

    key = OptionSetKey.AREA_AWARE_MEDIA_PLAYER
    options = [
        MagicAreasConfigOption(
            AreaAwareMediaPlayerOptionKey.NOTIFICATION_DEVICES, validator=cv.entity_ids
        ),
        MagicAreasConfigOption(
            AreaAwareMediaPlayerOptionKey.NOTIFY_STATES,
            validator=cv.ensure_list,
            default=[AreaState.EXTENDED],
            options=[AreaState.OCCUPIED, AreaState.EXTENDED, AreaState.SLEEP],
        ),
    ]


class PresenceHoldOptionKey(StrEnum):
    """Option keys for presence hold option set."""

    TIMEOUT = "presence_hold_timeout"


class PresenceHoldOptionSet(MagicAreasConfigOptionSet):
    """Presence hold option set."""

    key = OptionSetKey.PRESENCE_HOLD
    options = [
        MagicAreasConfigOption(
            PresenceHoldOptionKey.TIMEOUT, validator=cv.positive_int, default=0
        )
    ]


class AreaHealthOptionKey(StrEnum):
    """Option keys for area health option set."""

    DEVICE_CLASSES = "health_sensor_device_classes"


class AreaHealthOptionSet(MagicAreasConfigOptionSet):
    """Area health option set."""

    key = OptionSetKey.AREA_HEALTH
    options = [
        MagicAreasConfigOption(
            AreaHealthOptionKey.DEVICE_CLASSES,
            validator=cv.ensure_list,
            default=DISTRESS_SENSOR_CLASSES,
            options=DISTRESS_SENSOR_CLASSES,
        )
    ]


class AggregatesOptionKey(StrEnum):
    """Option keys for aggregates option set."""

    MIN_ENTITIES = "aggregates_min_entities"
    BINARY_SENSOR_DEVICE_CLASSES = "aggregates_binary_sensor_device_classes"
    SENSOR_DEVICE_CLASSES = "aggregates_sensor_device_classes"
    ILLUMINANCE_THRESHOLD = "aggregates_illuminance_threshold"
    MODE_ALL = "aggregate_mode_all"
    MODE_SUM = "aggregate_mode_sum"
    SENSOR_METRICS_TOTAL = "aggregate_metrics_total_sensor"
    SENSOR_PRECISION = "aggregate_sensor_precision"


class AggregatesOptionSet(MagicAreasConfigOptionSet):
    """Aggregates option set."""

    key = OptionSetKey.AGGREGATES
    options = [
        MagicAreasConfigOption(
            AggregatesOptionKey.MIN_ENTITIES, validator=cv.positive_int, default=2
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.BINARY_SENSOR_DEVICE_CLASSES,
            validator=cv.ensure_list,
            default=ALL_BINARY_SENSOR_DEVICE_CLASSES,
            options=ALL_BINARY_SENSOR_DEVICE_CLASSES,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.SENSOR_DEVICE_CLASSES,
            validator=cv.ensure_list,
            default=ALL_SENSOR_DEVICE_CLASSES,
            options=ALL_SENSOR_DEVICE_CLASSES,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.ILLUMINANCE_THRESHOLD,
            validator=cv.positive_int,
            default=0,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.MODE_ALL,
            validator=list,
            default=[
                BinarySensorDeviceClass.CONNECTIVITY,
                BinarySensorDeviceClass.PLUG,
            ],
            configurable=False,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.MODE_SUM,
            validator=list,
            default=[
                SensorDeviceClass.POWER,
                SensorDeviceClass.CURRENT,
                SensorDeviceClass.ENERGY,
            ],
            configurable=False,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.SENSOR_METRICS_TOTAL,
            validator=list,
            default=[SensorDeviceClass.ENERGY],
            configurable=False,
        ),
        MagicAreasConfigOption(
            AggregatesOptionKey.SENSOR_PRECISION,
            validator=int,
            default=2,
            configurable=False,
        ),
    ]


ALL_OPTION_SETS = [
    AreaInfoOptionSet,
    SecondaryStatesOptionSet,
    LightGroupOptionSet,
    ClimateGroupOptionSet,
    AreaAwareMediaPlayerOptionSet,
    PresenceHoldOptionSet,
    AreaHealthOptionSet,
    AggregatesOptionSet,
]

# Base Classes


class MagicAreasConfig:
    """Magic Areas configuration object."""

    _config_object: dict = None
    _option_sets: dict[str, MagicAreasConfigOptionSet]

    def __init__(self, config_object: dict | None = None) -> None:
        """Initialize option sets and load config if provided."""

        # Load and map option sets
        for option_set_class in ALL_OPTION_SETS:
            option_set = option_set_class()
            self._option_sets[option_set.key] = option_set

        if config_object:
            self._load_config(config_object)

    def _load_config(self, config_object: dict) -> None:
        """Loads current option values from dictionary."""

        if OptionSetKey.SECONDARY_STATES in config_object:
            self._option_sets[OptionSetKey.SECONDARY_STATES].load(
                config_object[OptionSetKey.SECONDARY_STATES]
            )
            del config_object[OptionSetKey.SECONDARY_STATES]

        self._option_sets[OptionSetKey.AREA_INFO].load(config_object)

    def get(self, option_set_key: str) -> MagicAreasConfigOptionSet:
        """Return option set for given key."""

        if option_set_key not in self._option_sets:
            raise ValueError(f"Invalid option: {option_set_key}")

        return self._option_sets.get(option_set_key)


CONF_FEATURE_LIST_META = [
    MagicAreasFeatures.MEDIA_PLAYER_GROUPS,
    MagicAreasFeatures.LIGHT_GROUPS,
    MagicAreasFeatures.COVER_GROUPS,
    MagicAreasFeatures.CLIMATE_GROUPS,
    MagicAreasFeatures.AGGREGATES,
    MagicAreasFeatures.HEALTH,
]

CONF_FEATURE_LIST = CONF_FEATURE_LIST_META + [
    MagicAreasFeatures.AREA_AWARE_MEDIA_PLAYER,
    MagicAreasFeatures.PRESENCE_HOLD,
]

CONF_FEATURE_LIST_GLOBAL = CONF_FEATURE_LIST_META

CONFIGURABLE_AREA_STATE_MAP = {
    AreaState.SLEEP: SecondaryStatesOptionKey.SLEEP_ENTITY,
    AreaState.DARK: SecondaryStatesOptionKey.AREA_LIGHT_SENSOR,
    AreaState.ACCENT: SecondaryStatesOptionKey.ACCENT_ENTITY,
}
LIGHT_GROUP_CATEGORIES = [
    LightGroupOptionKey.OVERHEAD_LIGHTS,
    LightGroupOptionKey.SLEEP_LIGHTS,
    LightGroupOptionKey.ACCENT_LIGHTS,
    LightGroupOptionKey.TASK_LIGHTS,
]
