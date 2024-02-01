from collections.abc import Iterable

from custom_components.magic_areas.const import (
    MODULE_DATA,
    DATA_AREA_OBJECT,
)

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