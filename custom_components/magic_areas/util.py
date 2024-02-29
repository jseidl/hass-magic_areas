import logging
import inspect
from collections.abc import Iterable

from homeassistant.helpers.area_registry import AreaEntry
from homeassistant.util import slugify

from custom_components.magic_areas.const import (
    MODULE_DATA,
    DATA_AREA_OBJECT,
    EVENT_MAGICAREAS_AREA_READY,
)

_LOGGER = logging.getLogger(__name__)

basestring = (str, bytes)

def is_entity_list(item):
    return isinstance(item, Iterable) and not isinstance(item, basestring)


def flatten_entity_list(input_list):
    for i in input_list:
        if is_entity_list(i):
            for sublist in flatten_entity_list(i):
                yield sublist
        else:
            yield i

def areas_loaded(hass):

    if MODULE_DATA not in hass.data.keys():
        return False

    data = hass.data[MODULE_DATA]
    for area_info in data.values():
        area = area_info[DATA_AREA_OBJECT]
        if not area.is_meta():
            if not area.initialized:
                return False

    return True

def add_entities_when_ready(hass, async_add_entities, config_entry, callback_fn):
    
    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Run right away if area is ready
    if area.initialized:
        callback_fn(area, async_add_entities)
    else:

        callback = None

        async def load_entities(event):

            if config_entry.entry_id not in ma_data.keys():
                _LOGGER.warn(f"Config entry id {config_entry.entry_id} not in Magic Areas data.")
                return False

            if area.id != event.data.get('id'):
                return False
            
            # Destroy listener
            if callback:
                callback()

            try:
                callback_fn(area, async_add_entities)
            except Exception as e:
                _LOGGER.exception(f"[{area.name}] Error loading platform entities on {str(callback_fn)}.")

        # These sensors need to wait for the area object to be fully initialized
        callback = hass.bus.async_listen(
            EVENT_MAGICAREAS_AREA_READY, load_entities
        )

def get_meta_area_object(name):
    
    area_slug = slugify(name) 

    params = {
        'name': name,
        'normalized_name': area_slug,
        'aliases': set(),
        'id': area_slug,
        'picture': None,
        'icon': None,
        'floor_id': None,
        'labels': set()
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