"""Binary sensor control for magic areas."""

from datetime import UTC, datetime, timedelta
import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
    call_later,
)

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicSelectEntity
from .base.magic import MagicArea, StateConfigData
from .base.primitives import BinarySensorBase, BinarySensorGroupBase
from .const import (
    AGGREGATE_MODE_ALL,
    ALL_LIGHT_ENTITIES,
    ATTR_ACTIVE_AREAS,
    ATTR_ACTIVE_SENSORS,
    ATTR_AREAS,
    ATTR_CLEAR_TIMEOUT,
    ATTR_LAST_ACTIVE_SENSORS,
    ATTR_PRESENCE_SENSORS,
    ATTR_STATE,
    ATTR_TYPE,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIMEOUT,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_PRESENCE_HOLD,
    DEFAULT_CLEAR_TIMEOUT,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DISTRESS_SENSOR_CLASSES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
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

        self._name = f"Area ({self.area.name})"

        self.last_off_time = datetime.now(UTC)
        self._clear_timeout_callback = None
        self._attributes = {}
        self.sensors = []
        self._mode = "some"

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

    async def _setup_listeners(self, _=None) -> None:
        self.logger.debug("%s: Called '_setup_listeners'", self.name)
        if not self.hass.is_running:
            self.logger.debug("%s: Cancelled '_setup_listeners'", self.name)
            return

        # Track presence sensors
        assert self.hass
        self.async_on_remove(
            async_track_state_change(self.hass, self.sensors, self._sensor_state_change)
        )

        # Track secondary states
        for _state, conf in self.area.all_state_configs():
            if not conf.has_entity:
                continue

            self.logger.debug("Secondary state tracking: %s", conf.entity)

            self.async_on_remove(
                async_track_state_change(
                    self.hass, conf.entity, self._secondary_state_change
                )
            )

        # Timed self update
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))
        self.async_on_remove(
            async_track_time_interval(self.hass, self._refresh_states, delta)
        )

    def _load_presence_sensors(self) -> None:
        if self.area.is_meta():
            # MetaAreas track their children
            child_areas = self.area.get_child_areas()
            for child_area in child_areas:
                entity_id = f"{BINARY_SENSOR_DOMAIN}.area_{child_area}"
                self.sensors.append(entity_id)
            return

        valid_presence_platforms = self.area.config.get(
            CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS
        )

        for component, entities in self.area.entities.items():
            if component not in valid_presence_platforms:
                continue

            for entity in entities:
                if not entity:
                    continue

                if component == BINARY_SENSOR_DOMAIN:
                    if ATTR_DEVICE_CLASS not in entity:
                        continue

                    if entity[ATTR_DEVICE_CLASS] not in self.area.config.get(
                        CONF_PRESENCE_SENSOR_DEVICE_CLASS
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

        if self.area.is_meta():
            self._attributes[ATTR_ACTIVE_AREAS] = self.area.get_active_areas()

    ####
    ####     State Change Handling
    def get_current_area_state(self) -> AreaState:
        """Get the current state for the area based on the various entities and controls."""
        # Get Main occupancy state
        occupied_state = self._get_occupancy_state()

        seconds_since_last_change = (
            datetime.now(UTC) - self.area.last_changed
        ).total_seconds()

        extended_time = self.area.config.get(
            CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT
        )
        if not occupied_state:
            if seconds_since_last_change <= extended_time:
                return AreaState.AREA_STATE_EXTENDED
            return AreaState.AREA_STATE_CLEAR

        # If it is not occupied, then set the override state or leave as just occupied.
        state = AreaState.AREA_STATE_OCCUPIED

        for state, conf in self.area.all_state_configs():
            if conf.entity is None:
                continue

            entity = self.hass.states.get(conf.entity)

            if entity.state.lower() == conf.entity_state_on:
                self.logger.debug(
                    "%s: Secondary state: %s is at %s, adding %s",
                    self.area.name,
                    conf.entity,
                    conf.entity_state_on,
                    conf.enable_state,
                )
                state = conf.enable_state

        return state

    def _get_occupancy_state(self) -> AreaState:
        valid_on_states = (
            [STATE_ON] if self.area.is_meta() else self.area.config.get(CONF_ON_STATES)
        )
        area_state = self.get_sensors_state(valid_states=valid_on_states)

        if not area_state:
            if not self.area.is_occupied():
                return False

            if self._is_on_clear_timeout():
                self.logger.debug("%s: Area is on timeout", self.area.name)
                if self._timeout_exceeded():
                    return False
            else:
                self.logger.debug(
                    "%s: Area not on timeout, setting call_later", self.area.name
                )
                self._set_clear_timeout()
        else:
            self._remove_clear_timeout()

        return True

    def _update_state(self):
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

        self.logger.debug(
            "%s: States updated. New states: %s / Last states: %s",
            self.area.name,
            new_state,
            last_state,
        )

        self._update_attributes()
        self.schedule_update_ha_state()

        self._report_state_change(
            (new_state, last_state, self.area.state_config(last_state))
        )

    def _report_state_change(
        self, states_tuple: tuple[AreaState, AreaState, StateConfigData | None]
    ):
        new_states, lost_states = states_tuple
        self.logger.debug(
            "Reporting state change for %s (new state: %s/last state: %s)",
            self.area.name,
            new_states,
            lost_states,
        )
        dispatcher_send(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area.id, states_tuple
        )

    def _secondary_state_change(
        self, entity_id: str, from_state: State, to_state: State
    ):
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

    def _get_clear_timeout(self):
        return self.area.config.get(CONF_CLEAR_TIMEOUT)

    def _set_clear_timeout(self):
        if not self.area.is_occupied():
            return False

        timeout = self._get_clear_timeout()

        self.logger.debug("%s: Scheduling clear in %s seconds", self.area.name, timeout)
        self._clear_timeout_callback = call_later(
            self.hass, timeout, self._refresh_states
        )

    def _remove_clear_timeout(self):
        if not self._clear_timeout_callback:
            return False

        self._clear_timeout_callback()
        self._clear_timeout_callback = None

    def _is_on_clear_timeout(self):
        return self._clear_timeout_callback is not None

    #### Sensor controls.

    def _refresh_states(self, next_interval: int):
        self.logger.debug("Refreshing sensor states %s", self.name)
        return self._update_state()

    def _timeout_exceeded(self):
        if not self.area.is_occupied():
            return False

        clear_delta = timedelta(seconds=self._get_clear_timeout())

        last_clear = self.last_off_time
        clear_time = last_clear + clear_delta
        time_now = datetime.now(UTC)

        if time_now >= clear_time:
            self.logger.debug("%s: Clear Timeout exceeded", self.area.name)
            self._remove_clear_timeout()
            return True

        return False

    def _sensor_state_change(self, entity_id: str, from_state: State, to_state: State):
        """Actions when the sensor state has changed."""
        _LOGGER.warning(
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

        if to_state and to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.now(UTC)  # Update last_off_time

        return self._update_state()

    def _get_sensors_state(self, valid_states: list | None = None) -> bool:
        """Get the current state of the sensor."""
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
