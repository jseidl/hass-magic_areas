"""Cover controls for magic areas."""

import logging

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import CONF_FEATURE_COVER_GROUPS
from custom_components.magic_areas.add_entities_when_ready import (
    add_entities_when_ready,
)
import homeassistant.components.cover as cover
from homeassistant.components.group.cover import CoverGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_cover_groups)


def add_cover_groups(area: MagicArea, async_add_entities: AddEntitiesCallback):
    # Check feature availability
    if not area.has_feature(CONF_FEATURE_COVER_GROUPS):
        return

    # Check if there are any covers
    if not area.has_entities(cover.DOMAIN):
        _LOGGER.debug(f"No {cover.DOMAIN} entities for area {area.name} ")
        return

    entities_to_add = []

    # Append None to the list of device classes to catch those covers that
    # don't have a device class assigned (and put them in their own group)
    for device_class in cover.DEVICE_CLASSES + [None]:
        covers_in_device_class = [
            e["entity_id"]
            for e in area.entities[cover.DOMAIN]
            if e.get("device_class") == device_class
        ]

        if any(covers_in_device_class):
            _LOGGER.debug(
                f"Creating {device_class or ''} cover group for {area.name} with covers: {covers_in_device_class}"
            )
            entities_to_add.append(AreaCoverGroup(area, device_class))
    async_add_entities(entities_to_add)


class AreaCoverGroup(MagicEntity, CoverGroup):
    def __init__(self, area: MagicArea, device_class):
        MagicEntity.__init__(self, area)

        if device_class:
            device_class_name = " ".join(device_class.split("_")).title()
            self._name = f"Area Covers ({device_class_name}) ({area.name})"
        else:
            self._name = f"Area Covers ({area.name})"

        self._device_class = device_class
        self._entities = [
            e
            for e in area.entities[cover.DOMAIN]
            if e.get("device_class") == device_class
        ]
        self._attributes["entity_id"] = [e["entity_id"] for e in self._entities]

        CoverGroup.__init__(
            self, self.unique_id, self._name, self._attributes["entity_id"]
        )

    @property
    def device_class(self):
        return self._device_class
