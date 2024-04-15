"""Magic Areas Util Functions.

Small helper functions that are used more than once.
"""

from collections.abc import Iterable
import logging

from homeassistant.helpers.area_registry import AreaEntry
from homeassistant.util import slugify

from .const import DATA_AREA_OBJECT, EVENT_MAGICAREAS_AREA_READY, MODULE_DATA

_LOGGER = logging.getLogger(__name__)

basestring = (str, bytes)


class BasicArea:
    """An interchangeable area object for Magic Areas to consume."""

    id = None
    name = None


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


def add_entities_when_ready(hass, async_add_entities, config_entry, callback_fn):
    """Add entities to Home Assistant when Magic Area finishes initializing."""

    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Run right away if area is ready
    if area.initialized:
        callback_fn(area, async_add_entities)
    else:
        callback = None

        async def load_entities(event):
            if config_entry.entry_id not in ma_data:
                _LOGGER.warning(
                    "Config entry id '%s' not in Magic Areas data.",
                    config_entry.entry_id,
                )
                return False

            if area.id != event.data.get("id"):
                return False

            # Destroy listener
            if callback:
                callback()

            try:
                callback_fn(area, async_add_entities)
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception:
                _LOGGER.exception(
                    "%s: Error loading platform entities on '%s'.",
                    area.name,
                    str(callback_fn),
                )

        # These sensors need to wait for the area object to be fully initialized
        callback = hass.bus.async_listen(EVENT_MAGICAREAS_AREA_READY, load_entities)


def basic_area_from_name(name) -> BasicArea:
    """Create a BasicArea from a name."""

    area = BasicArea()
    area.name = name
    area.id = slugify(name)

    return area


def basic_area_from_object(area: AreaEntry) -> BasicArea:
    """Create a BasicArea from an AreaEntry object."""

    basic_area = BasicArea()
    basic_area.name = area.name
    basic_area.id = area.id

    return basic_area
