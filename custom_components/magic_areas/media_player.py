DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.media_player import SUPPORT_PLAY_MEDIA, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
)

_LOGGER = logging.getLogger(__name__)

from .const import CONF_NOTIFICATION_DEVICES, MODULE_DATA, CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER, META_AREA_GLOBAL, DATA_AREA_OBJECT

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    
    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Check if we are the Global Meta Area
    if not area.is_meta() or area.id != META_AREA_GLOBAL.lower():
        _LOGGER.warn(f"This feature is only available for the Global Meta-Area")
        return

    # Check if feature is enabled
    if not area.has_feature(CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER):
        return

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    areas_with_media_players = []

    for entry in ma_data.values():
        
        area = entry[DATA_AREA_OBJECT]

        # Skip meta areas
        if area.is_meta():
            continue

        if MEDIA_PLAYER_DOMAIN in area.entities.keys():
            areas_with_media_players.append(area)

    if not areas_with_media_players:
        _LOGGER.warn(f"No areas with {MEDIA_PLAYER_DOMAIN} entities. Skipping creation of area-aware-media-player")
        return

    async_add_entities([AreaAwareMediaPlayer(hass, areas_with_media_players)])

class AreaAwareMediaPlayer(MediaPlayerEntity):
    def __init__(self, hass, areas):

        self.hass = hass

        self._name = "Area-Aware Media Player"
        
        self.entity_id = f"{MEDIA_PLAYER_DOMAIN}.area_aware_media_player"

        self._attributes = {}
        self._state = STATE_IDLE

        self.areas = areas
        self._tracked_entities = []

        for area in self.areas:

            entity_list = self.get_media_players_for_area(area)
            
            self._tracked_entities.extend(entity_list)

        self._update_state()

        _LOGGER.info(f"AreaAwareMediaPlayer loaded.")

    def _update_attributes(self):

        self._attributes["areas"] = [f"binary_sensor.area_{area.slug}" for area in self.areas]
        self._attributes["entities"] = self._tracked_entities
        self._attributes["last_active_areas"] = [f"binary_sensor.area_{area.slug}" for area in self._get_active_areas()]

    def get_media_players_for_area(self, area):

        entity_ids = []

        notification_devices = area.config.get(CONF_NOTIFICATION_DEVICES)

        for entity in area.entities[MEDIA_PLAYER_DOMAIN]:
                entity_ids.append(entity['entity_id'])

        # Return the notification_devices if defined and all valid
        if notification_devices:
            all_valid_devices = all([device in entity_ids for device in notification_devices])
            if all_valid_devices:
                return set(notification_devices)

        # Return all media_player entities
        return set(entity_ids)

    @property
    def unique_id(self):
        """Return a unique ID."""
        return "{MEDIA_PLAYER_DOMAIN}_area_aware_media_player"

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the attributes of the media player."""
        return self._attributes

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
            area_binary_sensor_name = f"binary_sensor.area_{area.slug}"
            area_binary_sensor_state = self.hass.states.get(area_binary_sensor_name)

            if not area_binary_sensor_state:
                _LOGGER.debug(f"No state found for entity {area_binary_sensor_name}")
                continue

            if area_binary_sensor_state.state == STATE_ON:
                active_areas.append(area)

        return active_areas


    def _update_state(self):

        self._update_attributes()
        self.schedule_update_ha_state()

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

        self._update_state()
        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data)
