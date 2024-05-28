"""The basic entities for magic areas."""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import DOMAIN, MAGIC_DEVICE_ID_PREFIX
from ..util import slugify
from .magic import MagicArea

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea = None

    def __init__(self, area: MagicArea) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        self.area = area

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        name_slug = slugify(self._attr_name)
        return f"{name_slug}"

    @property
    def should_poll(self) -> str:
        """If entity should be polled."""
        return False

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.area.id}")
            },
            name=self.area.name,
            manufacturer="Simply Magic Areas",
            model="Simply Magic Area",
        )
