"""Utility details for the system."""

from collections.abc import Callable
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base.magic import MagicArea
from .const import DATA_AREA_OBJECT, EVENT_MAGICAREAS_AREA_READY, MODULE_DATA

_LOGGER = logging.getLogger(__name__)


def add_entities_when_ready(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: ConfigEntry,
    callback_fn: Callable[[MagicArea, AddEntitiesCallback], None],
    with_hass: bool = False,
) -> None:
    """Add entities into the system when it is ready to add."""
    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Run right away if area is ready
    if area.initialized:
        if with_hass:
            callback_fn(area, hass, async_add_entities)
        else:
            callback_fn(area, async_add_entities)
    else:
        callback = None

        async def load_entities(event):
            if config_entry.entry_id not in ma_data:
                _LOGGER.warning(
                    "Config entry id %s not in Magic Areas data", config_entry.entry_id
                )
                return False

            if area.id != event.data.get("id"):
                return False

            # Destroy listener
            if callback:
                callback()

            try:
                if with_hass:
                    callback_fn(area, hass, async_add_entities)
                else:
                    callback_fn(area, async_add_entities)
            # pylint: disable-next=broad-exception-caught
            except Exception:
                _LOGGER.exception(
                    "[%s Error loading platform entities on %s",
                    area.name,
                    str(callback_fn),
                )

        # These sensors need to wait for the area object to be fully initialized
        callback = hass.bus.async_listen(EVENT_MAGICAREAS_AREA_READY, load_entities)
