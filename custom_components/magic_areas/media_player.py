DEPENDENCIES = ["media_player"]

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.media_player import SUPPORT_PLAY_MEDIA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.components.group.media_player import MediaGroup
from homeassistant.const import (
    ATTR_ENTITY_ID, 
    STATE_IDLE, 
    STATE_ON, 
    SERVICE_TURN_OFF,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.dispatcher import async_dispatcher_connect

_LOGGER = logging.getLogger(__name__)

from .base import MagicEntity
from .const import (
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_ON_SLEEP,
    DATA_AREA_OBJECT,
    META_AREA_GLOBAL,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):

    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Media Player Groups
    if area.has_feature(CONF_FEATURE_MEDIA_PLAYER_GROUPS):
        _LOGGER.debug(f"{area.name}: Setting up media player groups")
        setup_media_player_group(hass, area, async_add_entities)

    # Check if we are the Global Meta Area
    if not area.is_meta() or area.id != META_AREA_GLOBAL.lower():
        _LOGGER.debug("{area.name}: Not Global Meta-Area, skipping.")
        return

    # Area-Aware Media Player
    if area.has_feature(CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER):
        _LOGGER.debug(f"{area.name}: Setting up area-aware media player")
        setup_area_aware_media_player(hass, ma_data)

def setup_media_player_group(hass, area, async_add_entities):

    # Check if there are any lights
    if not area.has_entities(MEDIA_PLAYER_DOMAIN):
        _LOGGER.debug(f"No {MEDIA_PLAYER_DOMAIN} entities for area {area.name} ")
        return

    media_player_entities = [e["entity_id"] for e in area.entities[MEDIA_PLAYER_DOMAIN]]

    async_add_entities([AreaMediaGroup(hass, area, media_player_entities)])

def setup_area_aware_media_player(hass, ma_data, async_add_entities):

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    areas_with_media_players = []

    for entry in ma_data.values():
        current_area = entry[DATA_AREA_OBJECT]

        # Skip meta areas
        if current_area.is_meta():
            continue

        if current_area.has_entities(MEDIA_PLAYER_DOMAIN):
            areas_with_media_players.append(current_area)

    if not areas_with_media_players:
        _LOGGER.warning(
            f"No areas with {MEDIA_PLAYER_DOMAIN} entities. Skipping creation of area-aware-media-player"
        )
        return

    async_add_entities([AreaAwareMediaPlayer(hass, area, areas_with_media_players)])


class AreaAwareMediaPlayer(MagicEntity, MediaPlayerEntity, RestoreEntity):
    def __init__(self, hass, area, areas):

        self.hass = hass

        self._name = "Area-Aware Media Player"

        self._attributes = {}
        self._state = STATE_IDLE

        self.areas = areas
        self.area = area
        self._tracked_entities = []

        for area in self.areas:

            entity_list = self.get_media_players_for_area(area)

            self._tracked_entities.extend(entity_list)

        _LOGGER.info(f"AreaAwareMediaPlayer loaded.")

    def _update_attributes(self):

        self._attributes["areas"] = [
            f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}" for area in self.areas
        ]
        self._attributes["entities"] = self._tracked_entities

    def get_media_players_for_area(self, area):

        entity_ids = []

        notification_devices = self.area.feature_config(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
        ).get(CONF_NOTIFICATION_DEVICES)

        area_media_players = [
            entity["entity_id"] for entity in area.entities[MEDIA_PLAYER_DOMAIN]
        ]

        # Check if media_player entities are notification devices
        for mp in area_media_players:
            if mp in notification_devices:
                entity_ids.append(mp)

        return set(entity_ids)

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""

        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug(
                f"Nedia Player {self.name} restored [state={last_state.state}]"
            )
            self._state = last_state.state
        else:
            self._state = STATE_IDLE

        self.set_state()

    @property
    def state(self):
        """Return the state of the media player"""
        return self._state

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_PLAY_MEDIA

    def _get_active_areas(self):

        active_areas = []

        for area in self.areas:
            area_binary_sensor_name = f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}"
            area_binary_sensor_state = self.hass.states.get(area_binary_sensor_name)

            if not area_binary_sensor_state:
                _LOGGER.debug(f"No state found for entity {area_binary_sensor_name}")
                continue

            # Check NOTIFY_ON_SLEEP
            if area.is_sleeping() and not self.area.feature_config(
                CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
            ).get(CONF_NOTIFY_ON_SLEEP):
                _LOGGER.debug(f"Area {area.name} is sleeping, skipping")
                continue

            if area_binary_sensor_state.state == STATE_ON:
                active_areas.append(area)

        return active_areas

    def _update_state(self):

        self._update_attributes()
        self.schedule_update_ha_state()

    def set_state(self, state=None):
        if state:
            self._state = state
        self._update_state()

    def play_media(self, media_type, media_id, **kwargs):
        """Forwards a piece of media to media players in active areas."""

        # Read active areas
        active_areas = self._get_active_areas()

        # Fail early
        if not active_areas:
            _LOGGER.info("No areas active. Ignoring.")
            return False

        # Gather media_player entities
        media_players = []
        for area in active_areas:
            media_players.extend(self.get_media_players_for_area(area))

        if not media_players:
            _LOGGER.info("No media_player entities to forward. Ignoring.")
            return False

        data = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: media_players,
        }

        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data)

        return True

class AreaMediaGroup(MagicEntity, MediaGroup):
    def __init__(self, hass, area, entities):

        name = f"{area.name} Media Players"

        self._name = name
        self._entities = entities

        self.hass = hass
        self.area = area

        MediaGroup.__init__(self, self._name, self._entities)

        _LOGGER.debug(
            f"Media Player group {self._name} created with entities: {self._entities}"
        )

    def area_state_changed(self, area_id, new_states):
    
        if area_id != self.area.id:
            _LOGGER.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        _LOGGER.debug(f"Media Player group {self.name} detected area state change")

        if not self.area.is_occupied():
            _LOGGER.debug(f"{self.area.name}: Area clear, turning off media players")
            self.turn_off()

    def turn_off(self):

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        async_dispatcher_connect(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
        )

        await super().async_added_to_hass()