"""Media player pieces for the system."""

import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.group.media_player import MediaPlayerGroup
from homeassistant.components.media_player import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    DOMAIN as MEDIA_PLAYER_DOMAIN,
    SERVICE_PLAY_MEDIA,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, STATE_IDLE, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.area_registry import AreaEntry, async_get as async_get_ar
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    DEFAULT_NOTIFICATION_DEVICES,
    DEFAULT_NOTIFY_STATES,
    META_AREA_GLOBAL,
)

DEPENDENCIES = ["media_player"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the media player entities."""
    add_entities_when_ready(hass, async_add_entities, config_entry, add_media_players)


def add_media_players(area: MagicArea, async_add_entities: AddEntitiesCallback) -> None:
    """Create the media players."""
    # Media Player Groups
    if area.has_feature(CONF_FEATURE_MEDIA_PLAYER_GROUPS):
        _LOGGER.debug("%s: Setting up media player groups", area.name)
        setup_media_player_group(area, async_add_entities)

    # Check if we are the Global Meta Area
    if not area.is_meta() or area.id != META_AREA_GLOBAL.lower():
        _LOGGER.debug("%s: Not Global Meta-Area, skipping", area.name)
        return

    # Try to setup AAMP
    _LOGGER.debug("Trying to setup AAMP")
    setup_area_aware_media_player(area, async_add_entities)


def setup_media_player_group(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Create the media player group."""
    # Check if there are any media player devices
    if not area.has_entities(MEDIA_PLAYER_DOMAIN):
        _LOGGER.debug("No %s entities for area %s", MEDIA_PLAYER_DOMAIN, area.name)
        return

    media_player_entities = [e["entity_id"] for e in area.entities[MEDIA_PLAYER_DOMAIN]]

    async_add_entities([AreaMediaPlayerGroup(area, media_player_entities)])


async def setup_area_aware_media_player(
    hass: HomeAssistant, area: MagicArea, async_add_entities: AddEntitiesCallback
) -> None:
    """Create the area aware media player."""
    registry = async_get_ar(hass)

    # Check if we have areas with MEDIA_PLAYER_DOMAIN entities
    areas_with_media_players = []

    for entry in registry.areas:
        current_area = registry.async_get_area(entry)

        # Skip meta areas
        if current_area.is_meta():
            _LOGGER.debug("%s: Is meta-area, skipping", current_area.name)
            continue

        # Skip areas with feature not enabled
        if not current_area.has_feature(CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER):
            _LOGGER.debug(
                "%s: Does not have AAMP feature enabled, skipping", current_area.name
            )
            continue

        # Skip areas without media player entities
        if not current_area.has_entities(MEDIA_PLAYER_DOMAIN):
            _LOGGER.debug(
                "%s: Has no media player entities, skipping", current_area.name
            )
            continue

        # Skip areas without notification devices set
        notification_devices = current_area.feature_config(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
        ).get(CONF_NOTIFICATION_DEVICES)

        if not notification_devices:
            _LOGGER.debug(
                "%s: Has no notification devices, skipping", current_area.name
            )
            continue

        # If all passes, we add this valid area to the list
        areas_with_media_players.append(current_area)

    if not areas_with_media_players:
        _LOGGER.debug(
            "No areas with %s entities. Skipping creation of area-aware-media-player",
            MEDIA_PLAYER_DOMAIN,
        )
        return

    area_names = [i.name for i in areas_with_media_players]

    _LOGGER.debug(
        "%s: Setting up area-aware media player with areas: %s", area.name, area_names
    )
    async_add_entities([AreaAwareMediaPlayer(area, areas_with_media_players)])


class AreaAwareMediaPlayer(MagicEntity, MediaPlayerEntity, RestoreEntity):
    """Media player that is area aware."""

    def __init__(self, area: MagicArea, areas: list[AreaEntry]) -> None:
        """Initialize the area aware media player."""
        super().__init__(area)

        self._name = "Area-Aware Media Player"

        self._attributes = {}
        self._state = STATE_IDLE

        self.logger = _LOGGER

        self.areas = areas
        self.area = area
        self._tracked_entities = []

        for area in self.areas:
            entity_list = self._get_media_players_for_area(area)
            if entity_list:
                self._tracked_entities.extend(entity_list)

        self.logger.info("AreaAwareMediaPlayer loaded")

    def _update_attributes(self):
        self._attributes["areas"] = [
            f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}" for area in self.areas
        ]
        self._attributes["entity_id"] = self._tracked_entities

    def _get_media_players_for_area(self, area):
        entity_ids = []

        notification_devices = area.feature_config(
            CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER
        ).get(CONF_NOTIFICATION_DEVICES, DEFAULT_NOTIFICATION_DEVICES)

        self.logger.debug(f"{area.name}: Notification devices: {notification_devices}")

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
            self.logger.debug(
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
        return MediaPlayerEntityFeature.PLAY_MEDIA

    def get_active_areas(self):
        active_areas = []

        for area in self.areas:
            area_binary_sensor_name = f"{BINARY_SENSOR_DOMAIN}.area_{area.slug}"
            area_binary_sensor_state = self.hass.states.get(area_binary_sensor_name)

            if not area_binary_sensor_state:
                self.logger.debug(
                    f"No state found for entity {area_binary_sensor_name}"
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

    def _update_state(self):
        self._update_attributes()
        self.schedule_update_ha_state()

    def set_state(self, state=None):
        """Set the state for the media player."""
        if state:
            self._state = state
        self._update_state()

    def play_media(self, media_type, media_id, **kwargs):
        """Forward a piece of media to media players in active areas."""

        # Read active areas
        active_areas = self.get_active_areas()

        # Fail early
        if not active_areas:
            self.logger.info("No areas active. Ignoring.")
            return False

        # Gather media_player entities
        media_players = []
        for area in active_areas:
            media_players.extend(self._get_media_players_for_area(area))

        if not media_players:
            self.logger.info("No media_player entities to forward. Ignoring.")
            return False

        data = {
            ATTR_MEDIA_CONTENT_ID: media_id,
            ATTR_MEDIA_CONTENT_TYPE: media_type,
            ATTR_ENTITY_ID: media_players,
        }

        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_PLAY_MEDIA, data)

        return True


class AreaMediaPlayerGroup(MagicEntity, MediaPlayerGroup):
    def __init__(self, area, entities):
        MagicEntity.__init__(self, area)

        name = f"{area.name} Media Players"

        self._name = name
        self._entities = entities

        MediaPlayerGroup.__init__(self, self.unique_id, self._name, self._entities)

        self.logger.debug(
            f"Media Player group {self._name} created with entities: {self._entities}"
        )

    def _area_state_changed(
        self, entity_id: str, from_state: State, to_state: State
    ) -> None:
        new_states, lost_states = states_tuple

        if area_id != self.area.id:
            self.logger.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        self.logger.debug(f"Media Player group {self.name} detected area state change")

        if AREA_STATE_CLEAR in new_states:
            self.logger.debug(
                f"{self.area.name}: Area clear, turning off media players"
            )
            self._turn_off()

    def _turn_off(self):
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        self.async_on_remove(
            async_track_state_change(
                self.hass,
                [f"{SELECT_DOMAIN}.area_{self.area.slug}"],
                self._area_state_change,
            )
        )
        await super().async_added_to_hass()
