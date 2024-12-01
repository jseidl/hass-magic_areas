"""Magic Areas Area Helper Functions.

Small helper functions for area and Magic Area objects.
"""

import logging

from custom_components.magic_areas.base.magic import BasicArea, MagicArea, MagicMetaArea
from custom_components.magic_areas.const import (
    DATA_AREA_OBJECT,
    MODULE_DATA,
    MetaAreaType,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ID, ATTR_NAME

from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import (
    AreaEntry,
    async_get as areareg_async_get,
)
from homeassistant.helpers.floor_registry import (
    FloorEntry,
    async_get as floorreg_async_get,
)

_LOGGER = logging.getLogger(__name__)

def basic_area_from_meta(area_id: str, name: str | None = None) -> BasicArea:
    """Create a BasicArea from a name."""

    area = BasicArea()
    if not name:
        area.name = area_id.capitalize()
    area.id = area_id
    area.is_meta = True

    return area


def basic_area_from_object(area: AreaEntry) -> BasicArea:
    """Create a BasicArea from an AreaEntry object."""

    basic_area = BasicArea()
    basic_area.name = area.name
    basic_area.id = area.id
    basic_area.icon = area.icon
    basic_area.floor_id = area.floor_id

    return basic_area


def basic_area_from_floor(floor: FloorEntry) -> BasicArea:
    """Create a BasicArea from an AreaEntry object."""

    basic_area = BasicArea()
    basic_area.name = floor.name
    basic_area.id = floor.floor_id
    basic_area.icon = floor.icon
    basic_area.floor_id = floor.floor_id
    basic_area.is_meta = True

    return basic_area



def get_magic_area_for_config_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Return magic area object for given config entry."""

    area_id = config_entry.data[ATTR_ID]
    area_name = config_entry.data[ATTR_NAME]

    magic_area: MagicArea = None

    _LOGGER.debug("%s: Setting up entry.", area_name)

    # Load floors
    floor_registry = floorreg_async_get(hass)
    floors = floor_registry.async_list_floors()

    non_floor_meta_ids = [
        meta_area_type
        for meta_area_type in MetaAreaType
        if meta_area_type != MetaAreaType.FLOOR
    ]
    floor_ids = [f.floor_id for f in floors]

    if area_id in non_floor_meta_ids:
        # Non-floor Meta-Area (Global/Interior/Exterior)
        meta_area = basic_area_from_meta(area_id)
        magic_area = MagicMetaArea(hass, meta_area, config_entry)
    elif area_id in floor_ids:
        # Floor Meta-Area
        meta_area = basic_area_from_floor(floor_registry.async_get_floor(area_id))
        magic_area = MagicMetaArea(hass, meta_area, config_entry)
    else:
        # Regular Area
        area_registry = areareg_async_get(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.warning("%s: ID '%s' not found on registry", area_name, area_id)
            return False

        _LOGGER.debug("%s: Got area from registry: %s", area_name, str(area))

        magic_area = MagicArea(
            hass,
            basic_area_from_object(area),
            config_entry,
        )

    return magic_area


def get_area_from_config_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict | None:
    """Return area object for given config entry."""

    if config_entry.entry_id not in hass.data[MODULE_DATA]:
        return None

    return hass.data[MODULE_DATA][config_entry.entry_id][DATA_AREA_OBJECT]
