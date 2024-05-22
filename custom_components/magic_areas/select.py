"""Binary sensor control for magic areas."""

from datetime import UTC, datetime, timedelta
import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, State
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
    call_later,
)
from homeassistant.util.async_ import run_callback_threadsafe

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicSelectEntity
from .base.magic import MagicArea, MagicEvent
from .const import (
    ATTR_ACTIVE_AREAS,
    ATTR_ACTIVE_SENSORS,
    ATTR_AREAS,
    ATTR_CLEAR_TIMEOUT,
    ATTR_EXTENDED_TIMEOUT,
    ATTR_LAST_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
    ATTR_STATE,
    ATTR_TYPE,
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIMEOUT,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_ON_STATES,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
    DEFAULT_UPDATE_INTERVAL,
    INVALID_STATES,
    AreaState,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_state_select)


def add_state_select(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the basic sensors for the area."""
    # Create basic presence sensor
    async_add_entities([AreaStateSelect(area)])


class AreaStateSelect(MagicSelectEntity):
    """Create an area presence binary sensor that tracks the current occupied state."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        super().__init__(area, list(AreaState))

        self._name: str = f"Area ({self.area.name})"

        self.last_off_time: int = datetime.now(UTC)
        self._clear_timeout_callback = None
        self._extended_timeout_callback = None
        self._attributes: dict[str, any] = {}
        self.sensors: list[str] = []
        self._mode: str = "some"

    @property
    def icon(self) -> str | None:
        """Return the icon to be used for this entity."""
        if self.area.config.get(CONF_ICON):
            return self.area.config.get(CONF_ICON)
        return None

    async def restore_state(self) -> None:
        """Restore the state of the sensor on initialize."""
        last_state = await self.async_get_last_state()
        is_new_entry = last_state is None  # newly added to HA

        if is_new_entry:
            self.logger.debug("New sensor created: %s", self.name)
            self._update_state()
        else:
            _LOGGER.debug(
                "Sensor %s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self.area.state = last_state.attributes.get(
                ATTR_STATE, AreaState.AREA_STATE_CLEAR
            )
            self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing", self.name)

        self._load_presence_sensors()
        self._load_attributes()

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug("%s Sensor initialized", self.name)

    def _async_registry_updated(self, event: Event[MagicEvent]):
        if event.data["id"] == self.area.id:
            # Event is for us.
            self._load_presence_sensors()
            self._setup_presence_listeners()

    async def _setup_listeners(self, _=None) -> None:
        self.logger.debug("%s: Called '_setup_listeners'", self.name)
        if not self.hass.is_running:
            self.logger.debug("%s: Cancelled '_setup_listeners'", self.name)
            return

        # Track presence sensor
        self.async_on_remove(
            async_track_state_change(self.hass, self.sensors, self._sensor_state_change)
        )

        # Track secondary states
        for state in self.area.all_state_configs():
            conf = self.area.all_state_configs()[state]

            if not conf.entity:
                continue

            self.logger.debug("State entity tracking: %s", conf.entity)

            self.async_on_remove(
                async_track_state_change(
                    self.hass, conf.entity, self._group_entity_state_change
                )
            )

        # Timed self update
        delta = timedelta(
            seconds=self.area.feature_config(CONF_FEATURE_ADVANCED_LIGHT_GROUPS).get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )
        )
        self.async_on_remove(
            async_track_time_interval(self.hass, self._update_state, delta)
        )

    def _load_presence_sensors(self) -> None:
        if self.area.is_meta():
            # MetaAreas track their children
            child_areas = self.area.get_child_areas()
            for child_area in child_areas:
                entity_id = f"{SELECT_DOMAIN}.area_{child_area}"
                self.sensors.append(entity_id)
            return

        valid_presence_platforms = self.area.feature_config(
            CONF_FEATURE_ADVANCED_LIGHT_GROUPS
        ).get(CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS)

        for component, entities in self.area.entities.items():
            if component not in valid_presence_platforms:
                continue

            for entity in entities:
                if not entity:
                    continue

                if component == BINARY_SENSOR_DOMAIN:
                    if ATTR_DEVICE_CLASS not in entity:
                        continue

                    if entity[ATTR_DEVICE_CLASS] not in self.area.feature_config(
                        CONF_FEATURE_ADVANCED_LIGHT_GROUPS
                    ).get(
                        CONF_PRESENCE_SENSOR_DEVICE_CLASS,
                        DEFAULT_PRESENCE_DEVICE_SENSOR_CLASS,
                    ):
                        continue

                self.sensors.append(entity[ATTR_ENTITY_ID])

    def _load_attributes(self) -> None:
        # Set attributes
        self._attributes = {}

        if not self.area.is_meta():
            self._attributes.update({ATTR_STATE: self.area.state})
        else:
            self._attributes.update(
                {
                    ATTR_AREAS: self.area.get_child_areas(),
                    ATTR_ACTIVE_AREAS: self.area.get_active_areas(),
                }
            )

        # Add common attributes
        self._attributes.update(
            {
                ATTR_ACTIVE_SENSORS: [],
                ATTR_LAST_ACTIVE_SENSORS: [],
                ATTR_PRESENCE_SENSORS: self.sensors,
                ATTR_TYPE: self.area.config.get(CONF_TYPE),
            }
        )

    def _update_attributes(self):
        self._attributes[ATTR_STATE] = self.area.state
        self._attributes[ATTR_CLEAR_TIMEOUT] = self._get_clear_timeout()
        self._attributes[ATTR_EXTENDED_TIMEOUT] = self._get_extended_timeout()

        if self.area.is_meta():
            self._attributes[ATTR_ACTIVE_AREAS] = self.area.get_active_areas()

    ####
    ####     State Change Handling
    def get_current_area_state(self) -> AreaState:
        """Get the current state for the area based on the various entities and controls."""
        # Get Main occupancy state
        occupied_state = self._get_sensors_state()

        seconds_since_last_change = (
            datetime.now(UTC) - self.last_off_time
        ).total_seconds()

        extended_timeout = self._get_extended_timeout()
        clear_timeout = self._get_clear_timeout()
        _LOGGER.debug(
            "Update state seconds since %s timout %s, extended %s, is_on_clear %s, is_on_extended %s",
            seconds_since_last_change,
            clear_timeout,
            extended_timeout,
            self._is_on_clear_timeout(),
            self._is_on_extended_timeout(),
        )
        if not occupied_state:
            if not self._is_on_clear_timeout():
                self._set_clear_timeout()
            if seconds_since_last_change >= clear_timeout:
                if seconds_since_last_change >= extended_timeout:
                    self._remove_extended_timeout()
                    return AreaState.AREA_STATE_CLEAR
                _LOGGER.debug("Clearing teimput, state extended")
                self._remove_clear_timeout()
                if not self._is_on_extended_timeout():
                    self._set_extended_timeout()
                return AreaState.AREA_STATE_EXTENDED
        else:
            self._remove_clear_timeout()
            self._remove_extended_timeout()

        # If it is not occupied, then set the override state or leave as just occupied.
        new_state = AreaState.AREA_STATE_OCCUPIED

        for state in self.area.all_state_configs():
            conf = self.area.all_state_configs()[state]
            if conf.entity is None:
                continue

            entity = self.hass.states.get(conf.entity)

            if entity is None:
                continue

            if entity.state.lower() == conf.entity_state_on:
                self.logger.debug(
                    "%s: Secondary state: %s is at %s, adding %s",
                    self.area.name,
                    conf.entity,
                    conf.entity_state_on,
                    conf.for_state,
                )
                new_state = conf.for_state

        return new_state

    def _update_state(self, extra=None) -> None:
        last_state = self.area.state
        new_state = self.get_current_area_state()

        if last_state == new_state:
            return

        # Calculate what's new
        self.logger.debug(
            "%s: Current state: %s, last state: %s",
            self.name,
            new_state,
            last_state,
        )

        # Update the state so the on/off works correctly.
        self.area.state = new_state
        self._attr_current_option = new_state

        self._update_attributes()
        self.schedule_update_ha_state()

        self.logger.debug(
            "Reporting state change for %s (new state: %s/last state: %s)",
            self.area.name,
            new_state,
            last_state,
        )

    def _group_entity_state_change(
        self, entity_id: str, from_state: State, to_state: State
    ) -> None:
        self.logger.debug(
            "%s: Secondary state change: entity '%s' changed to %s",
            self.area.name,
            entity_id,
            to_state.state,
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state %s",
                self.area.name,
                entity_id,
                to_state.state,
            )
            return None

        self._update_state()

    ###       Clearing

    def _get_clear_timeout(self) -> int:
        return int(self.area.config.get(CONF_CLEAR_TIMEOUT, 60))

    def _set_clear_timeout(self) -> None:
        if self._clear_timeout_callback:
            self._remove_clear_timeout()

        timeout = self._get_clear_timeout()

        self.logger.debug("%s: Scheduling clear in %s seconds", self.area.name, timeout)
        self._clear_timeout_callback = call_later(
            self.hass,
            timeout,
            self._update_state,
        )

    def _remove_clear_timeout(self) -> None:
        if not self._clear_timeout_callback:
            return False

        self.logger.debug(
            "%s: Clearing timeout",
            self.area.name,
        )

        self._clear_timeout_callback()
        self._clear_timeout_callback = None

    def _is_on_clear_timeout(self) -> None:
        return self._clear_timeout_callback is not None

    ###       Extended

    def _get_extended_timeout(self) -> int:
        return (
            int(self.area.config.get(CONF_EXTENDED_TIMEOUT, 60))
            + self._get_clear_timeout()
        )

    def _set_extended_timeout(self) -> None:
        if self._extended_timeout_callback:
            self._remove_extended_timeout()

        timeout = self._get_extended_timeout()

        self.logger.debug(
            "%s: Scheduling extended in %s seconds", self.area.name, timeout
        )
        self._extended_timeout_callback = call_later(
            self.hass,
            timeout,
            self._update_state,
        )

    def _remove_extended_timeout(self) -> None:
        if not self._extended_timeout_callback:
            return False

        self._extended_timeout_callback()
        self._extended_timeout_callback = None

    def _is_on_extended_timeout(self) -> None:
        return self._extended_timeout_callback is not None

    #### Sensor controls.

    def _clear_timeout_exceeded(self) -> bool:
        if not self.area.is_occupied():
            return False

        clear_delta = timedelta(seconds=self._get_clear_timeout())

        clear_time = self.last_off_time + clear_delta
        time_now = datetime.now(UTC)

        if time_now >= clear_time:
            self.logger.debug("%s: Clear Timeout exceeded", self.area.name)
            self._remove_clear_timeout()
            return True

        return False

    def _extended_timeout_exceeded(self) -> bool:
        if not self.area.is_occupied():
            return False

        extended_delta = timedelta(seconds=self._get_extended_timeout())

        extended_time = self.last_off_time + extended_delta
        time_now = datetime.now(UTC)

        if time_now >= extended_time:
            self.logger.debug("%s: Extended Timeout exceeded", self.area.name)
            self._remove_extended_timeout()
            return True

        return False

    def _sensor_state_change(
        self, entity_id: str, from_state: State, to_state: State
    ) -> None:
        """Actions when the sensor state has changed."""
        _LOGGER.debug(
            "Sensor state change %s from %s to %s", entity_id, from_state, to_state
        )
        if not to_state:
            return

        self.logger.debug(
            "%s: sensor '%s' changed to {%s}",
            self.name,
            entity_id,
            to_state.state,
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state %s",
                self.name,
                entity_id,
                to_state.state,
            )
            return

        if to_state and to_state.state not in self.area.feature_config(
            CONF_FEATURE_ADVANCED_LIGHT_GROUPS
        ).get(CONF_ON_STATES, DEFAULT_ON_STATES):
            _LOGGER.debug("Setting last non-normal time")
            self.last_off_time = datetime.now(UTC)  # Update last_off_time
            # Clear the timeout
            self._remove_clear_timeout()

        self._update_state()

    def _get_sensors_state(self) -> bool:
        """Get the current state of the sensor."""
        valid_states = (
            [STATE_ON]
            if self.area.is_meta()
            else self.area.feature_config(CONF_FEATURE_ADVANCED_LIGHT_GROUPS).get(
                CONF_ON_STATES, DEFAULT_ON_STATES
            )
        )

        self.logger.debug(
            "[Area: %s] Updating state. (Valid states: %s)",
            self.area.slug,
            valid_states,
        )

        if valid_states is None:
            valid_states = [STATE_ON]

        active_sensors = []
        active_areas = set()

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        "[Area: %s] Could not get sensor state: %s entity not found, skipping",
                        self.area.slug,
                        sensor,
                    )
                    continue

                self.logger.debug(
                    "[Area: %s] Sensor %s state: %s",
                    self.area.slug,
                    sensor,
                    entity.state,
                )

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    self.logger.debug(
                        "[Area: %s] Sensor '%s' is unavailable, skipping.",
                        self.area.slug,
                        sensor,
                    )
                    continue

                if entity.state in valid_states:
                    self.logger.debug(
                        "[Area: %s] Valid presence sensor found: %s.",
                        self.area.slug,
                        sensor,
                    )
                    active_sensors.append(sensor)

            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    "[%s] Error getting entity state for '%s': %s",
                    self.area.slug,
                    sensor,
                    str(e),
                )

        self._attributes["active_sensors"] = active_sensors

        # Make a copy that doesn't gets cleared out, for debugging
        if active_sensors:
            self._attributes["last_active_sensors"] = active_sensors

        self.logger.debug(
            "[Area: %s] Active sensors: %s",
            self.area.slug,
            active_sensors,
        )

        if self.area.is_meta():
            active_areas = self.area.get_active_areas()
            self.logger.debug(
                "[Area: %s] Active areas: %s",
                self.area.slug,
                active_areas,
            )
            self._attributes["active_areas"] = active_areas

        if self._mode == "all":
            return len(active_sensors) == len(self.sensors)
        return len(active_sensors) > 0
