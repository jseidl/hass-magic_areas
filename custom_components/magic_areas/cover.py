"""Platform file for Magic Area's cover entities."""

import logging

from homeassistant.components import cover
from homeassistant.components.group.cover import CoverGroup

from .base.entities import MagicEntity
from .const import CONF_FEATURE_COVER_GROUPS
from .util import add_entities_when_ready

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_cover_groups)


def add_cover_groups(area, async_add_entities):
    """Add all the cover entities for all features that have one."""
    # Check feature availability
    if not area.has_feature(CONF_FEATURE_COVER_GROUPS):
        return

    # Check if there are any covers
    if not area.has_entities(cover.DOMAIN):
        _LOGGER.debug("%s: No %s entities for area.", area.name, cover.DOMAIN)
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
                "%s: Creating %s cover group for with covers: %s",
                area.name,
                device_class or "",
                str(covers_in_device_class),
            )
            entities_to_add.append(AreaCoverGroup(area, device_class))
    async_add_entities(entities_to_add)


class AreaCoverGroup(MagicEntity, CoverGroup):
    """Cover group."""

    def __init__(self, area, device_class):
        """Initialize cover group."""

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
        """Return the cover device class."""
        return self._device_class
