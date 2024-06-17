"""Base classes for feature information."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN


class MagicAreasFeatureInfo:
    """Base class for feature information."""

    id: str
    translation_keys: dict[str, str]
    icons: dict[str, str] = {}


# Feature Information
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
