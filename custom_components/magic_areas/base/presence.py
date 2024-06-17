"""Main presence tracking entity for Magic Areas."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sun.const import STATE_ABOVE_HORIZON
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
    call_later,
)

from ..const import (
    CONFIGURABLE_AREA_STATE_MAP,
    INVALID_STATES,
    ONE_MINUTE,
    PRESENCE_SENSOR_VALID_ON_STATES,
    AreaInfoOptionKey,
    AreaState,
    CustomAttribute,
    MagicAreasEvent,
    MagicAreasFeatures,
    OptionSetKey,
    SecondaryStatesOptionKey,
)
from .magic import MagicArea

_LOGGER = logging.getLogger(__name__)


class AreaStateTracker:
    """Tracks an area's state by tracking the configured entities."""

    # Init & Teardown

    def __init__(self, hass: HomeAssistant, area: MagicArea) -> None:
        """Initialize the area tracker."""

        self.area: MagicArea = area
        self.hass: HomeAssistant = hass

        self._state: bool = False

        self._last_off_time: datetime = datetime.now(UTC) - timedelta(days=2)
        self._clear_timeout_callback: Callable[[], None] | None = None

        self._sensors: list[str] = []
        self._active_sensors: list[str] = []
        self._last_active_sensors: list[str] = []

        self._tracker_callbacks: list[Callable] = []

        self._load_presence_sensors()

        # Setup the listeners
        self._setup_listeners()

        _LOGGER.debug("%s: presence tracker initialized", self.area.name)

    def _track_listener(self, callback_listener: Callable) -> None:

        self._tracker_callbacks.append(callback_listener)

    def _setup_listeners(self) -> None:

        # Track presence sensor
        self._track_listener(
            async_track_state_change_event(
                self.hass, self._sensors, self._sensor_state_change
            )
        )

        # Track secondary states
        secondary_state_entities: list[str] = []
        configurable_states = self._get_configured_secondary_states()

        for configurable_state in configurable_states:

            configurable_state_entity = CONFIGURABLE_AREA_STATE_MAP[configurable_state]
            tracked_entity = (
                self.area.config.get(OptionSetKey.SECONDARY_STATES)
                .get(configurable_state_entity)
                .value()
            )

            if not tracked_entity:
                continue

            secondary_state_entities.append(tracked_entity)

        if secondary_state_entities:
            _LOGGER.debug(
                "%s: Secondary state tracking: %s",
                self.area.name,
                str(secondary_state_entities),
            )
            self._track_listener(
                async_track_state_change_event(
                    self.hass, secondary_state_entities, self._secondary_state_change
                )
            )

        # Timed self update
        delta = timedelta(
            seconds=self.area.config.get(OptionSetKey.AREA_INFO)
            .get(AreaInfoOptionKey.UPDATE_INTERVAL)
            .value()
        )
        self._track_listener(
            async_track_time_interval(self.hass, self._refresh_states, delta)
        )

    def get_tracked_entities(self) -> None:
        """Return tracked entity callbacks."""
        return self._tracker_callbacks

    # Public methods

    def get_sensors(self) -> list[str]:
        """Return sensors used for tracking."""
        return self._sensors

    def get_metadata(self) -> dict:
        """Return metadata information about the area's occupancy."""
        return {
            CustomAttribute.PRESENCE_SENSORS: self._sensors,
            CustomAttribute.ACTIVE_SENSORS: self._active_sensors,
            CustomAttribute.LAST_ACTIVE_SENSORS: self._last_active_sensors,
            CustomAttribute.STATES: self.area.states,
            CustomAttribute.CLEAR_TIMEOUT: self._get_clear_timeout() / ONE_MINUTE,
        }

    def force_update(self) -> None:
        """Force instant state update."""
        self._update_state()

    # Helpers

    def _valid_on_states(self, additional_states: list[str] | None = None) -> list[str]:
        """Return valid ON states for entities."""

        valid_states = PRESENCE_SENSOR_VALID_ON_STATES.copy()

        if additional_states:
            valid_states.extend(additional_states)

        return [STATE_ON] if self.area.is_meta() else valid_states

    def _get_configured_secondary_states(self) -> list[str]:
        """Return configured secondary states."""
        secondary_states = []

        for (
            configurable_state,
            configurable_state_entity,
        ) in CONFIGURABLE_AREA_STATE_MAP.items():

            secondary_state_entity = (
                self.area.config.get(OptionSetKey.SECONDARY_STATES)
                .get(configurable_state_entity)
                .value()
            )

            if not secondary_state_entity:
                continue

            secondary_states.append(configurable_state)

        return secondary_states

    def _refresh_states(self, next_interval) -> None:
        """Refresh sensor state from tracked sensors."""
        _LOGGER.debug("%s: Refreshing sensor states.", self.area.name)
        self._update_state()

    # Entity loading

    def _load_presence_sensors(self) -> None:
        """Load sensors that are relevant for presence sensing."""
        if self.area.is_meta():
            # MetaAreas track their children
            child_areas = self.area.get_child_areas()
            for child_area in child_areas:
                entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{child_area}_area_state"
                self._sensors.append(entity_id)
            return

        valid_presence_platforms = (
            self.area.config.get(OptionSetKey.AREA_INFO)
            .get(AreaInfoOptionKey.PRESENCE_SENSOR_DOMAINS)
            .value()
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

                    if (
                        entity[ATTR_DEVICE_CLASS]
                        not in self.area.config.get(OptionSetKey.AREA_INFO)
                        .get(AreaInfoOptionKey.PRESENCE_SENSOR_DEVICE_CLASSES)
                        .value()
                    ):
                        continue

                self._sensors.append(entity[ATTR_ENTITY_ID])

        # Append presence_hold switch as a presence_sensor
        if self.area.config.has_feature(MagicAreasFeatures.PRESENCE_HOLD):
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{self.area.slug}"
            )
            self._sensors.append(presence_hold_switch_id)

    # Entity state tracking & reporting
    def _secondary_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle area secondary state change event."""
        if event.data["new_state"] is None:
            return

        to_state = event.data["new_state"].state
        entity_id = event.data["entity_id"]

        _LOGGER.debug(
            "%s: Secondary state change: entity '%s' changed to %s",
            self.area.name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self.area.name,
                entity_id,
                to_state,
            )
            return None

        self._update_state()

    def _sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Actions when the sensor state has changed."""
        if event.data["new_state"] is None:
            return

        # Ignore state reports taht aren't really a state change
        if (
            event.data["old_state"]
            and event.data["new_state"].state == event.data["old_state"].state
        ):
            return

        to_state = event.data["new_state"].state
        entity_id = event.data["entity_id"]

        _LOGGER.debug(
            "%s: sensor '%s' changed to {%s}",
            self.area.name,
            entity_id,
            to_state,
        )

        if to_state in INVALID_STATES:
            _LOGGER.debug(
                "%s: sensor '%s' has invalid state %s",
                self.area.name,
                entity_id,
                to_state,
            )
            return

        if to_state and to_state not in self._valid_on_states():
            _LOGGER.debug(
                "Setting last non-normal time %s %s",
                event.data["old_state"],
                event.data["new_state"],
            )
            self._last_off_time = datetime.now(UTC)  # Update last_off_time
            # Clear the timeout
            self._remove_clear_timeout()

        self._update_state()

    def _update_state(self) -> None:
        """Update the area's state and report changes."""

        states_tuple = self._update_area_states()
        new_states, lost_states = states_tuple

        state_changed = any(
            state in new_states for state in [AreaState.OCCUPIED, AreaState.CLEAR]
        )

        _LOGGER.debug(
            "%s: States updated. New states: %s / Lost states: %s",
            self.area.name,
            str(new_states),
            str(lost_states),
        )

        if state_changed:
            # Consider all secondary states new
            states_tuple = (self.area.states.copy(), [])

        self._report_state_change(states_tuple)

    def _report_state_change(self, states_tuple=([], [])):
        """Fire an event reporting area state change."""
        new_states, lost_states = states_tuple
        _LOGGER.debug(
            "%s: Reporting state change (new states: %s/lost states: %s)",
            self.area.name,
            str(new_states),
            str(lost_states),
        )
        dispatcher_send(
            self.hass, MagicAreasEvent.AREA_STATE_CHANGED, self.area.id, states_tuple
        )

        event_data = {
            "area_id": self.area.id,
            "new_states": new_states,
            "lost_states": lost_states,
        }
        self.hass.bus.fire(MagicAreasEvent.AREA_STATE_CHANGED, event_data=event_data)

    # Area state calculations

    def _update_area_states(self) -> tuple[list[str], list[str]]:
        """Return new and lost states for this area."""

        last_state = set(self.area.states.copy())
        current_state = set(self._get_area_states())

        if last_state == current_state:
            return ([], [])

        # Calculate what's new
        new_states = current_state - last_state
        lost_states = last_state - current_state
        _LOGGER.debug(
            "%s: Current state: %s, last state: %s -> new states %s / lost states %s",
            self.area.name,
            str(current_state),
            str(last_state),
            str(new_states),
            str(lost_states),
        )

        self.area.states = list(current_state)

        return (new_states, lost_states)

    def _get_area_states(self) -> list[str]:
        """Return states for the area."""
        states = []

        # Get Main occupancy state
        current_state = self._get_occupancy_state()
        last_state = self.area.is_occupied()

        states.append(AreaState.OCCUPIED if current_state else AreaState.CLEAR)
        if current_state != last_state:
            self.area.last_changed = datetime.now(UTC)
            _LOGGER.debug(
                "%s: State changed to %s at %s",
                self.area.name,
                current_state,
                self.area.last_changed,
            )

        seconds_since_last_change = (
            datetime.now(UTC) - self.area.last_changed
        ).total_seconds()

        extended_time = (
            self.area.config.get(OptionSetKey.SECONDARY_STATES)
            .get(SecondaryStatesOptionKey.EXTENDED_TIME)
            .value()
        )

        if (
            AreaState.OCCUPIED in states
            and (seconds_since_last_change / ONE_MINUTE) >= extended_time
        ):
            states.append(AreaState.EXTENDED)

        configurable_states = self._get_configured_secondary_states()

        # Assume AreaState.DARK if not configured
        if AreaState.DARK not in configurable_states:
            states.append(AreaState.DARK)

        for configurable_state in configurable_states:
            configurable_state_entity = CONFIGURABLE_AREA_STATE_MAP[configurable_state]

            secondary_state_entity = (
                self.area.config.get(OptionSetKey.SECONDARY_STATES)
                .get(configurable_state_entity)
                .value()
            )

            if not secondary_state_entity:
                continue

            entity = self.hass.states.get(secondary_state_entity)
            has_valid_state = entity.state.lower() in self._valid_on_states(
                [STATE_ABOVE_HORIZON]
            )
            state_to_add = None

            # Handle dark state from light sensor as an inverted configurable state
            inverted_states = [AreaState.DARK]

            # Handle both forward and inverted configurable state
            if configurable_state in inverted_states:
                if not has_valid_state:
                    state_to_add = configurable_state
            else:
                if has_valid_state:
                    state_to_add = configurable_state

            if state_to_add:
                _LOGGER.debug(
                    "%s: Secondary state: %s is at %s, adding %s",
                    self.area.name,
                    secondary_state_entity,
                    entity.state.lower(),
                    configurable_state,
                )
                states.append(configurable_state)

        # Meta-state bright
        if AreaState.DARK in configurable_states and AreaState.DARK not in states:
            states.append(AreaState.BRIGHT)

        return states

    def _get_occupancy_state(self) -> bool:
        """Return occupancy state for an area."""

        area_state = self._get_sensors_state()

        if not area_state:
            if not self.area.is_occupied():
                return False

            if self._is_on_clear_timeout():
                _LOGGER.debug("%s: Area is on timeout", self.area.name)
                if self._timeout_exceeded():
                    return False
            else:
                if self.area.is_occupied() and not area_state:
                    _LOGGER.debug(
                        "%s: Area not on timeout, setting call_later", self.area.name
                    )
                    self._set_clear_timeout()
        else:
            self._remove_clear_timeout()

        return True

    def _get_sensors_state(self) -> bool:
        """Fetch state from tracked sensors."""

        valid_states = self._valid_on_states()

        _LOGGER.debug(
            "%s: Updating state. (Valid states: %s)",
            self.area.name,
            ",".join(valid_states),
        )

        active_sensors = []

        # Loop over all entities and check their state
        for sensor in self._sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    _LOGGER.info(
                        "%s: Could not get sensor state: '%s' entity not found, skipping",
                        self.area.name,
                        sensor,
                    )
                    continue

                _LOGGER.debug(
                    "%s: Sensor '%s' state: %s", self.area.name, sensor, entity.state
                )

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    _LOGGER.debug(
                        "%s: Sensor '%s' is unavailable, skipping...",
                        self.area.name,
                        sensor,
                    )
                    continue

                if entity.state in valid_states:
                    _LOGGER.debug(
                        "%s: Valid presence sensor found: %s.", self.area.name, sensor
                    )
                    active_sensors.append(sensor)

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.error(
                    "%s: Error getting entity state for '%s': %s",
                    self.area.name,
                    sensor,
                    str(e),
                )

        # Populate metadata
        self._active_sensors = active_sensors

        if active_sensors:
            self._last_active_sensors = active_sensors

        return len(active_sensors) > 0

    # Clear timeout

    def _set_clear_timeout(self):
        """Set clear timeout."""
        if not self.area.is_occupied():
            return False

        timeout = self._get_clear_timeout()

        _LOGGER.debug("%s: Scheduling clear in %s seconds", self.area.name, timeout)
        self._clear_timeout_callback = call_later(
            self.hass, timeout, self._refresh_states
        )

        # Schedule task for cancellation on removal
        self._track_listener(self._clear_timeout_callback)

    def _get_clear_timeout(self) -> int:
        """Return configured clear timeout value."""
        if self.area.has_state(AreaState.SLEEP):
            return (
                self.area.config.get(OptionSetKey.SECONDARY_STATES)
                .get(SecondaryStatesOptionKey.SLEEP_TIMEOUT)
                .value()
                * ONE_MINUTE
            )

        if self.area.has_state(AreaState.EXTENDED):
            return (
                self.area.config.get(OptionSetKey.SECONDARY_STATES)
                .get(SecondaryStatesOptionKey.EXTENDED_TIMEOUT)
                .value()
                * ONE_MINUTE
            )

        return (
            self.area.config.get(OptionSetKey.AREA_INFO)
            .get(AreaInfoOptionKey.CLEAR_TIMEOUT)
            .value()
            * ONE_MINUTE
        )

    def _remove_clear_timeout(self) -> None:
        if not self._clear_timeout_callback:
            return

        _LOGGER.debug(
            "%s: Clearing timeout",
            self.area.name,
        )

        # pylint: disable-next=not-callable
        self._clear_timeout_callback()
        self._clear_timeout_callback = None

    def _is_on_clear_timeout(self) -> bool:
        return self._clear_timeout_callback is not None

    def _timeout_exceeded(self) -> bool:
        """Check if clear timeout is exceeded."""
        if not self.area.is_occupied():
            return False

        clear_delta = timedelta(seconds=self._get_clear_timeout())

        last_clear = self._last_off_time
        clear_time = last_clear + clear_delta
        time_now = datetime.now(UTC)

        if time_now >= clear_time:
            _LOGGER.debug("%s: Clear Timeout exceeded.", self.area.name)
            self._remove_clear_timeout()
            return True

        return False
