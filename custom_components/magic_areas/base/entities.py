"""The basic entities for magic areas."""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import DOMAIN, MAGICAREAS_UNIQUEID_PREFIX, MagicAreasFeatures
from .magic import MagicArea

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea = None

    _magicareas_feature_id: MagicAreasFeatures | None = None

    def __init__(self, area: MagicArea) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(type(self).__module__)
        self._attributes = {}

        self.area = area

        unique_id = self._generaete_unique_id()
        _LOGGER.warning(f">>>>> {unique_id}")

    def _generaete_unique_id(self, extra_parts: list | None = None):

        # Format: magicareas_feature_domain_areaname_name

        unique_id_parts = [MAGICAREAS_UNIQUEID_PREFIX]

        # Feature name
        if self._magicareas_feature_id:
            unique_id_parts.append(self._magicareas_feature_id)

        unique_id_parts.append(self.platform.platform_name)
        unique_id_parts.append(self.area.name)

        if extra_parts:
            unique_id_parts.extend(extra_parts)

        return '_'.join(unique_id_parts)

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
