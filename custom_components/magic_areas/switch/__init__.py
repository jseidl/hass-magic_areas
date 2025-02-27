"""Platform file for Magic Area's switch entities."""

import logging

from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    MagicAreasFeatureInfoLightGroups,
    MagicAreasFeatureInfoMediaPlayerGroups,
    MagicAreasFeatures,
)
from custom_components.magic_areas.helpers.area import get_area_from_config_entry
from custom_components.magic_areas.switch.base import SwitchBase
from custom_components.magic_areas.switch.climate_control import ClimateControlSwitch
from custom_components.magic_areas.switch.presence_hold import PresenceHoldSwitch
from custom_components.magic_areas.util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the area switch config entry."""

    area: MagicArea | None = get_area_from_config_entry(hass, config_entry)
    assert area is not None

    switch_entities = []

    if area.has_feature(MagicAreasFeatures.PRESENCE_HOLD):
        switch_entities.append(PresenceHoldSwitch(area))

    if area.has_feature(MagicAreasFeatures.LIGHT_GROUPS):
        switch_entities.append(LightControlSwitch(area))

    if area.has_feature(MagicAreasFeatures.MEDIA_PLAYER_GROUPS):
        switch_entities.append(MediaPlayerControlSwitch(area))

    if area.has_feature(MagicAreasFeatures.CLIMATE_CONTROL):
        switch_entities.append(ClimateControlSwitch(area))

    if switch_entities:
        async_add_entities(switch_entities)

    if SWITCH_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, switch_entities, area.magic_entities[SWITCH_DOMAIN]
        )


class LightControlSwitch(SwitchBase):
    """Switch to enable/disable light control."""

    feature_info = MagicAreasFeatureInfoLightGroups()
    _attr_entity_category = EntityCategory.CONFIG


class MediaPlayerControlSwitch(SwitchBase):
    """Switch to enable/disable media player control."""

    feature_info = MagicAreasFeatureInfoMediaPlayerGroups()
    _attr_entity_category = EntityCategory.CONFIG
