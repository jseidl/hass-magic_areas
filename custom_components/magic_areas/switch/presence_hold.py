"""Presence hold switch."""

from homeassistant.const import EntityCategory

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    MagicAreasFeatureInfoPresenceHold,
    MagicAreasFeatures,
)
from custom_components.magic_areas.switch.base import ResettableSwitchBase


class PresenceHoldSwitch(ResettableSwitchBase):
    """Switch to enable/disable presence hold."""

    feature_info = MagicAreasFeatureInfoPresenceHold()
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, area: MagicArea) -> None:
        """Initialize the switch."""

        timeout = area.feature_config(MagicAreasFeatures.PRESENCE_HOLD).get(
            CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
        )

        ResettableSwitchBase.__init__(self, area, timeout=timeout)
