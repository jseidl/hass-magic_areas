"""Utility details for the system."""

import logging
from typing import Protocol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base.magic import MagicArea
from .const import DATA_AREA_OBJECT, EVENT_MAGICAREAS_AREA_READY, MODULE_DATA

_LOGGER = logging.getLogger(__name__)


class AddEntitiesWhenReadyCallback(Protocol):
    """Protocol type for add_entities_when_ready callback."""

    def __call__(
        self, area: MagicArea, add_entity_callback: AddEntitiesCallback
    ) -> None:
        """Define add_entities type."""


def add_entities_when_ready(
    hass: HomeAssistant,
    async_add_entities: AddEntitiesCallback,
    config_entry: ConfigEntry,
    callback_fn: AddEntitiesWhenReadyCallback,
) -> None:
    """Add entities into the system when it is ready to add."""
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
                    "Config entry id %s not in Magic Areas data", config_entry.entry_id
                )
                return False

            if area.id != event.data.get("id"):
                return False

            # Destroy listener
            if callback:
                callback()

            try:
                callback_fn(area, async_add_entities)
            except Exception as e:
                _LOGGER.exception(
                    "[%s Error loading platform entities on %s",
                    area.name,
                    str(callback_fn),
                )

        # These sensors need to wait for the area object to be fully initialized
        callback = hass.bus.async_listen(EVENT_MAGICAREAS_AREA_READY, load_entities)
