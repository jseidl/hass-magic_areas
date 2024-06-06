"""Cover controls for magic areas."""

import logging

from homeassistant.components.cover import (
    DEVICE_CLASSES as COVER_DEVICE_CLASSES,
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.components.group.cover import CoverGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import CONF_FEATURE_COVER_GROUPS, MagicAreasFeatureInfoCoverGroups
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, _add_cover_groups)


def _add_cover_groups(area: MagicArea, async_add_entities: AddEntitiesCallback):
    # Check feature availability
    if not area.has_feature(CONF_FEATURE_COVER_GROUPS):
        return

    # Check if there are any covers
    if not area.has_entities(COVER_DOMAIN):
        _LOGGER.debug("No %s entities for area %s", COVER_DOMAIN, area.name)
        return

    entities_to_add = []

    # Append None to the list of device classes to catch those covers that
    # don't have a device class assigned (and put them in their own group)
    for device_class in [*COVER_DEVICE_CLASSES, None]:
        covers_in_device_class = [
            e["entity_id"]
            for e in area.entities[COVER_DOMAIN]
            if e.get("device_class") == device_class
        ]

        if any(covers_in_device_class):
            _LOGGER.debug(
                "Creating %s cover group for %s with covers: %s",
                device_class,
                area.name,
                covers_in_device_class,
            )
            entities_to_add.append(AreaCoverGroup(area, device_class))

    if entities_to_add:
        async_add_entities(entities_to_add)

    if COVER_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities_to_add, area.magic_entities[COVER_DOMAIN]
        )


class AreaCoverGroup(MagicEntity, CoverGroup):
    """Cover group for handling all the covers in the area."""

    feature_info = MagicAreasFeatureInfoCoverGroups()

    def __init__(self, area: MagicArea, device_class: str) -> None:
        """Initialize the cover group."""
        MagicEntity.__init__(
            self, area, domain=COVER_DOMAIN, translation_key=device_class
        )
        self._attr_device_class = device_class
        self._entities = [
            e
            for e in area.entities[COVER_DOMAIN]
            if e.get("device_class") == device_class
        ]
        CoverGroup.__init__(
            self,
            entities=[e["entity_id"] for e in self._entities],
            name=None,
            unique_id=self._attr_unique_id,
        )
        delattr(self, "_attr_name")
