"""The basic entities for magic areas."""

import logging

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from ..const import (
    DOMAIN,
    MAGIC_DEVICE_ID_PREFIX,
    MAGICAREAS_UNIQUEID_PREFIX,
    MagicAreasFeatureInfo,
)
from .magic import MagicArea

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea = None
    feature_info: MagicAreasFeatureInfo | None = None
    _extra_identifiers: list[str] = None
    _attr_has_entity_name = True

    def __init__(
        self,
        area: MagicArea,
        domain: str,
        translation_key: str | None = None,
        extra_identifiers: list[str] | None = None,
    ) -> None:
        """Initialize the magic area."""
        # Avoiding using super() due multiple inheritance issues
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(type(self).__module__)
        self.area = area
        self._extra_identifiers = []

        if extra_identifiers:
            self._extra_identifiers.extend(extra_identifiers)

        # Allow supplying of additional translation key parts
        # for dealing with device_classes
        translation_key_parts = []
        feature_translation_key = self.feature_info.translation_keys[domain]
        if feature_translation_key:
            translation_key_parts.append(feature_translation_key)
        if translation_key:
            translation_key_parts.append(translation_key)
        self._attr_translation_key = "_".join(translation_key_parts)
        self._attr_translation_placeholders = {}

        # Resolve icon
        self._attr_icon = self.feature_info.icons.get(domain, None)

        # Resolve entity id & unique id
        self.entity_id = self._generate_entity_id(domain)
        self._attr_unique_id = self._generaete_unique_id(domain)

        _LOGGER.debug(
            "%s: Initializing entity. (entity_id: %s, unique id: %s, translation_key: %s)",
            self.area.name,
            self.entity_id,
            self._attr_unique_id,
            self._attr_translation_key,
        )

    def _generate_entity_id(self, domain: str):

        entity_id_parts = [
            MAGICAREAS_UNIQUEID_PREFIX,
            self.feature_info.id,
            self.area.slug,
        ]

        if (
            self._attr_translation_key
            and self._attr_translation_key != self.feature_info.id
        ):
            entity_id_parts.append(self._attr_translation_key)

        if self._extra_identifiers:
            entity_id_parts.extend(self._extra_identifiers)

        entity_id = "_".join(entity_id_parts)

        return f"{domain}.{entity_id}"

    def _generaete_unique_id(self, domain: str, extra_parts: list | None = None):

        # Format: magicareas_feature_domain_areaname_name

        unique_id_parts = [
            MAGICAREAS_UNIQUEID_PREFIX,
            self.feature_info.id,
            domain,
            self.area.slug,
        ]

        if self._attr_translation_key:
            unique_id_parts.append(self._attr_translation_key)

        if self._extra_identifiers:
            unique_id_parts.extend(self._extra_identifiers)

        return "_".join(unique_id_parts)

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
            manufacturer="Magic Areas",
            model="Magic Area",
        )
