"""Platform file for Magic Area's media_player entities."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.group.media_player import MediaPlayerGroup
from homeassistant.components.media_player import (
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_IDLE, STATE_ON
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .const import (
    AREA_STATE_CLEAR,
    AREA_STATE_SLEEP,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    DATA_AREA_OBJECT,
    DEFAULT_NOTIFICATION_DEVICES,
    DEFAULT_NOTIFY_STATES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    META_AREA_GLOBAL,
    MODULE_DATA,
    MagicAreasFeatureInfoAreaAwareMediaPlayer,
    MagicAreasFeatureInfoMediaPlayerGroups,
)
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""
    add_entities_when_ready(hass, async_add_entities, config_entry, add_media_players)


def add_media_players(area, async_add_entities):
    """Add all the media_player entities for all features that have one."""

    entities_to_add: list[str] = []

    # Media Player Groups
    if area.has_feature(CONF_FEATURE_MEDIA_PLAYER_GROUPS):
        _LOGGER.debug("%s: Setting up media player groups.", area.name)
        entities_to_add.extend(setup_media_player_group(area))

    # Check if we are the Global Meta Area
    if area.is_meta() and area.id == META_AREA_GLOBAL.lower():
        # Try to setup AAMP
        _LOGGER.debug("%s: Setting up Area-Aware media player", area.name)
        entities_to_add.extend(setup_area_aware_media_player(area))

    if entities_to_add:
        async_add_entities(entities_to_add)

    if MEDIA_PLAYER_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities_to_add, area.magic_entities[MEDIA_PLAYER_DOMAIN]
        )


def setup_media_player_group(area):
    """Create the media player groups."""
    # Check if there are any media player devices
    if not area.has_entities(MEDIA_PLAYER_DOMAIN):
        _LOGGER.debug("%s: No %s entities.", area.name, MEDIA_PLAYER_DOMAIN)
        return []

    media_player_entities = [e["entity_id"] for e in area.entities[MEDIA_PLAYER_DOMAIN]]

    return [AreaMediaPlayerGroup(area, media_player_entities)]


def setup_area_aware_media_player(area):
    """Create Area-aware media player."""
    ma_data = area.hass.data[MODULE_DATA]

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    areas_with_media_players = []

    for entry in ma_data.values():
        current_area = entry[DATA_AREA_OBJECT]

        # Skip meta areas
        if current_area.is_meta():
            _LOGGER.debug("%s: Is meta-area, skipping.", current_area.name)
            continue

        # Skip areas with feature not enabled
        if not current_area.has_feature(CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER):
            _LOGGER.debug(
                "%s: Does not have Area-aware media player feature enabled, skipping.",
                current_area.name,
            )
            continue

        # Skip areas without media player entities
        if not current_area.has_entities(MEDIA_PLAYER_DOMAIN):
            _LOGGER.debug(
                "%s: Has no media player entities, skipping.", current_area.name
            )
            continue

        # Skip areas without notification devices set
        notification_devices = current_area.feature_config(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
        ).get(CONF_NOTIFICATION_DEVICES)

        if not notification_devices:
            _LOGGER.debug(
                "%s: Has no notification devices, skipping.", current_area.name
            )
            continue

        # If all passes, we add this valid area to the list
        areas_with_media_players.append(current_area)

    if not areas_with_media_players:
        _LOGGER.debug(
            "No areas with %s entities. Skipping creation of area-aware-media-player",
            MEDIA_PLAYER_DOMAIN,
        )
        return []

    area_names = [i.name for i in areas_with_media_players]

    _LOGGER.debug(
        "%s: Setting up area-aware media player with areas: %s", area.name, area_names
    )

    return [AreaAwareMediaPlayer(area, areas_with_media_players)]


class AreaAwareMediaPlayer(MagicEntity, MediaPlayerEntity):
    """Area-aware media player."""

    feature_info = MagicAreasFeatureInfoAreaAwareMediaPlayer()

    def __init__(self, area, areas):
        """Initialize area-aware media player."""
        MagicEntity.__init__(self, area, domain=MEDIA_PLAYER_DOMAIN)
        MediaPlayerEntity.__init__(self)

        self._attr_extra_state_attributes = {}
        self._state = STATE_IDLE

        self.areas = areas
        self.area = area
        self._tracked_entities = []

        for area_obj in self.areas:
            entity_list = self.get_media_players_for_area(area_obj)
            if entity_list:
                self._tracked_entities.extend(entity_list)

        _LOGGER.info("AreaAwareMediaPlayer loaded.")

    def update_attributes(self):
        """Update entity attributes."""
        self._attr_extra_state_attributes["areas"] = [
            f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}" for area in self.areas
        ]
        self._attr_extra_state_attributes["entity_id"] = self._tracked_entities

    def get_media_players_for_area(self, area):
        """Return media players for a given area."""
        entity_ids = []

        notification_devices = area.feature_config(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
        ).get(CONF_NOTIFICATION_DEVICES, DEFAULT_NOTIFICATION_DEVICES)

        _LOGGER.debug("%s: Notification devices: %s", area.name, notification_devices)

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
                "%s: Nedia Player restored [state=%s]", self.name, last_state.state
            )
            self._state = last_state.state
        else:
            self._state = STATE_IDLE

        self.set_state()

    @property
    def state(self):
        """Return the state of the media player."""
        return self._state

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return MediaPlayerEntityFeature.PLAY_MEDIA

    def get_active_areas(self):
        """Return areas that are occupied."""
        active_areas = []

        for area in self.areas:
            area_binary_sensor_name = f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}"
            area_binary_sensor_state = self.hass.states.get(area_binary_sensor_name)

            if not area_binary_sensor_state:
                _LOGGER.debug(
                    "%s: No state found for entity '%s'",
                    self.name,
                    area_binary_sensor_name,
                )
                continue

            # Ignore not occupied areas
            if area_binary_sensor_state.state != STATE_ON:
                continue

            # Check notification states
            notification_states = area.feature_config(
                CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
            ).get(CONF_NOTIFY_STATES, DEFAULT_NOTIFY_STATES)

            # Check sleep
            if area.has_state(AREA_STATE_SLEEP) and (
                AREA_STATE_SLEEP not in notification_states
            ):
                continue

            # Check other states
            has_valid_state = False
            for notification_state in notification_states:
                if area.has_state(notification_state):
                    has_valid_state = True

            # Append area
            if has_valid_state:
                active_areas.append(area)

        return active_areas

    def update_state(self):
        """Update entity state and attributes."""
        self.update_attributes()
        self.schedule_update_ha_state()

    def set_state(self, state=None):
        """Set the entity state."""
        if state:
            self._state = state
        self.update_state()

    def play_media(self, media_type, media_id, **kwargs):
        """Forward a piece of media to media players in active areas."""

        # Read active areas
        active_areas = self.get_active_areas()

        # Fail early
        if not active_areas:
            _LOGGER.info("No areas active. Ignoring.")
            return False

        # Gather media_player entities
        media_players = []
        for area in active_areas:
            media_players.extend(self.get_media_players_for_area(area))

        if not media_players:
            _LOGGER.info(
                "%s: No media_player entities to forward. Ignoring.", self.name
            )
            return False

        data = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: media_players,
        }

        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data)

        return True


class AreaMediaPlayerGroup(MagicEntity, MediaPlayerGroup):
    """Media player group."""

    feature_info = MagicAreasFeatureInfoMediaPlayerGroups()

    def __init__(self, area, entities):
        """Initialize media player group."""
        MagicEntity.__init__(self, area, domain=MEDIA_PLAYER_DOMAIN)
        # @FIXME use name from translation. Coudln't get it working.
        MediaPlayerGroup.__init__(
            self,
            name="Media Players",
            unique_id=self._attr_unique_id,
            entities=entities,
        )

        self._entities = entities

        _LOGGER.debug(
            "%s: Media Player group created with entities: %s",
            self.area.name,
            str(self._entities),
        )

    def _is_control_enabled(self):
        """Check if media player control is enabled by checking media player control switch state."""

        entity_id = f"{SWITCH_DOMAIN}.magic_areas_media_player_groups_{self.area.slug}_media_player_control"
        switch_entity = self.hass.states.get(entity_id)

        if not switch_entity:
            return False

        return switch_entity.state.lower() == STATE_ON

    def area_state_changed(self, area_id, states_tuple):
        """Handle area state change event."""
        # pylint: disable-next=unused-variable
        new_states, lost_states = states_tuple

        # Do nothing if control is disabled
        if not self._is_control_enabled():
            _LOGGER.debug("%s: Control disabled, skipping.", self.name)
            return

        if area_id != self.area.id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (req: %s/self: %s)",
                self.name,
                area_id,
                self.area.id,
            )
            return

        _LOGGER.debug("%s: Media Player group detected area state change.", self.name)

        if AREA_STATE_CLEAR in new_states:
            _LOGGER.debug("%s: Area clear, turning off media players", self.name)
            self._turn_off()

    def _turn_off(self):
        """Turn off all members in group."""
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        async_dispatcher_connect(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
        )

        await super().async_added_to_hass()
