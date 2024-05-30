"""The basic entities for magic areas."""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import DOMAIN, MAGIC_DEVICE_ID_PREFIX
from .magic import MagicArea

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea = None

    def __init__(self, area: MagicArea) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(type(self).__module__)
        self._attributes = {}

        self.area = area

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.area.id}")
            },
            name=self.area.name,
            manufacturer="Magic Areas",
            model="Magic Area",
        )
