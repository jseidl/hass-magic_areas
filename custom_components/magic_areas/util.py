"""Magic Areas Util Functions.

Small helper functions that are used more than once.
"""

from collections.abc import Sequence
import logging

from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import async_get as entityreg_async_get

_LOGGER = logging.getLogger(__name__)


def cleanup_removed_entries(
    hass: HomeAssistant, entity_list: Sequence[Entity], old_ids: list[dict[str, str]]
) -> None:
    """Clean up old magic entities."""
    new_ids = [entity.entity_id for entity in entity_list]
    _LOGGER.debug(
        "Checking for cleanup. Old entity list: %s, New entity list: %s",
        old_ids,
        new_ids,
    )
    entity_registry = entityreg_async_get(hass)
    for entity_dict in old_ids:
        entity_id = entity_dict[ATTR_ENTITY_ID]
        if entity_id in new_ids:
            continue
        _LOGGER.debug("Cleaning up old entity %s", entity_id)
        entity_registry.async_remove(entity_id)
