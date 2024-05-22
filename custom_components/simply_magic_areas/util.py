"""Utility details for the system."""

from collections.abc import Iterable
import inspect

from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import AreaEntry
from homeassistant.util import slugify

from .const import DATA_AREA_OBJECT, MODULE_DATA

basestring = (str, bytes)


def is_entity_list(item) -> bool:
    """If this is an entity list."""
    return isinstance(item, Iterable) and not isinstance(item, basestring)


def flatten_entity_list(input_list):
    """Flatten the entity list."""
    for i in input_list:
        if is_entity_list(i):
            yield from flatten_entity_list(i)
        else:
            yield i


def areas_loaded(hass: HomeAssistant) -> bool:
    """Return the state of the area being loaded."""
    if MODULE_DATA not in hass.data:
        return False

    data = hass.data[MODULE_DATA]
    for area_info in data.values():
        area = area_info[DATA_AREA_OBJECT]
        if not area.is_meta():
            if not area.initialized:
                return False

    return True


def get_meta_area_object(name: str):
    """Get the meta area object from the entity."""
    area_slug = slugify(name)

    params = {
        "name": name,
        "normalized_name": area_slug,
        "aliases": set(),
        "id": area_slug,
        "picture": None,
        "icon": None,
        "floor_id": None,
        "labels": set(),
    }

    # We have to introspect the AreaEntry constructor
    # to know if a given param is available because usually
    # Home Assistant updates this object with new parameters in
    # the constructor without defaults and breaks this function
    # in particular.

    available_params = {}
    constructor_params = inspect.signature(AreaEntry.__init__).parameters

    for k, v in params.items():
        if k in constructor_params:
            available_params[k] = v

    return AreaEntry(**available_params)
