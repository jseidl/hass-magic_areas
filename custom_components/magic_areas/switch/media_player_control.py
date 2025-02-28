"""Media player control feature switch."""

import logging

from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, EntityCategory
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    AreaStates,
    MagicAreasEvents,
    MagicAreasFeatureInfoMediaPlayerGroups,
)
from custom_components.magic_areas.switch.base import SwitchBase

_LOGGER = logging.getLogger(__name__)


class MediaPlayerControlSwitch(SwitchBase):
    """Switch to enable/disable climate control."""

    feature_info = MagicAreasFeatureInfoMediaPlayerGroups()
    _attr_entity_category = EntityCategory.CONFIG

    media_player_group_id: str

    def __init__(self, area: MagicArea) -> None:
        """Initialize the Climate control switch."""

        SwitchBase.__init__(self, area)

        self.media_player_group_id = f"{MEDIA_PLAYER_DOMAIN}.magic_areas_media_player_groups_{self.area.slug}_media_player_group"

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, MagicAreasEvents.AREA_STATE_CHANGED, self.area_state_changed
            )
        )

    async def area_state_changed(self, area_id, states_tuple):
        """Handle area state change event."""

        if not self.is_on:
            self.logger.debug("%s: Control disabled. Skipping.", self.name)
            return

        if area_id != self.area.id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (event: %s/self: %s)",
                self.name,
                area_id,
                self.area.id,
            )
            return

        # pylint: disable-next=unused-variable
        new_states, lost_states = states_tuple

        if AreaStates.CLEAR in new_states:
            _LOGGER.debug("%s: Area clear, turning off media players.", self.name)
            await self.hass.services.async_call(
                MEDIA_PLAYER_DOMAIN,
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self.media_player_group_id},
            )
            return
