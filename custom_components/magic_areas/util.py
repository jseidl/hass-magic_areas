"""Magic Areas Util Functions.

Small helper functions that are used more than once.
"""

from collections.abc import Iterable
import logging

from homeassistant.helpers.area_registry import AreaEntry
from homeassistant.helpers.floor_registry import FloorEntry

from .const import DATA_AREA_OBJECT, MODULE_DATA

_LOGGER = logging.getLogger(__name__)

basestring = (str, bytes)


class BasicArea:
    """An interchangeable area object for Magic Areas to consume."""

    id: str
    name: str | None = None
    icon: str | None = None
    floor_id: str | None = None
    is_meta: bool = False


def is_entity_list(item):
    """Check if item is a list."""
    return isinstance(item, Iterable) and not isinstance(item, basestring)


def flatten_entity_list(input_list):
    """Recursively flatten a nested list into a flat list."""
    for i in input_list:
        if is_entity_list(i):
            yield from flatten_entity_list(i)
        else:
            yield i


def areas_loaded(hass):
    """Check if all Magic Areas are loaded."""

    if MODULE_DATA not in hass.data:
        return False

    data = hass.data[MODULE_DATA]
    for area_info in data.values():
        area = area_info[DATA_AREA_OBJECT]
        if not area.is_meta():
            if not area.initialized:
                return False

    return True


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
