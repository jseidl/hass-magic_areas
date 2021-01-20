DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    MediaPlayerEntity,
    SUPPORT_PLAY_MEDIA
)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    SERVICE_PLAY_MEDIA
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
)

_LOGGER = logging.getLogger(__name__)

from .const import (
    MODULE_DATA
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument

    areas = hass.data.get(MODULE_DATA)
    areas_with_media_players = []

    for area in areas:
        if MEDIA_PLAYER_DOMAIN in area.entities.keys():
            areas_with_media_players.append(area)

    if areas_with_media_players:
        async_add_entities([AreaAwareMediaPlayer(hass, areas_with_media_players)])

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class AreaAwareMediaPlayer(MediaPlayerEntity):
    def __init__(self, hass, areas):

        self.hass = hass

        self._name = "Area-Aware Media Player"
        self._attributes = {}
        self._state = STATE_IDLE
        self._tracked_entities = []
        self._tracked_areas = []
        self._device_area_mapping = {}

        for area in areas:
            
            _entity_ids = []
            _area_binary_sensor_id = f"binary_sensor.area_{area.slug}"
            self._tracked_areas.append(_area_binary_sensor_id)

            for entity in area.entities[MEDIA_PLAYER_DOMAIN]:
                self._tracked_entities.append(entity.entity_id)
                _entity_ids.append(entity.entity_id)

            self._device_area_mapping[_area_binary_sensor_id] = _entity_ids

        self._attributes['areas'] = self._tracked_areas
        self._attributes['entities'] = self._tracked_entities
        self._attributes['active_areas'] = []

        self._update_state()

        _LOGGER.info(f"AreaAwareMediaPlayer loaded.")

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

    def _update_state(self):

        _active_areas = []

        for entity_id in self._tracked_areas:
            area_binary_sensor = self.hass.states.get(entity_id)
            if area_binary_sensor.state == STATE_ON or 1==1:
                _active_areas.append(entity_id)

        self._attributes['active_areas'] = _active_areas
        self.schedule_update_ha_state()

    def play_media(self, media_type, media_id, **kwargs):
        """Forwards a piece of media to media players in active areas."""

        # Read active areas
        self._update_state()

        # Fail early
        if not self._attributes['active_areas']:
            _LOGGER.info("No areas active. Ignoring.")
            return False

        # Gather media_player entities
        _media_players = []
        for area in self._attributes['active_areas']:
            _media_players.extend(self._device_area_mapping[area])

        if not _media_players:
            _LOGGER.info("No media_player entities to forward. Ignoring.")
            return False

        data = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: _media_players,
        }

        self.hass.services.call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_PLAY_MEDIA,
            data
        )