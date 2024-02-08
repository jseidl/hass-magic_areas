import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    STATE_ON,
)
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
    call_later,
)

from custom_components.magic_areas.base.primitives import BinarySensorBase, BinarySensorGroupBase
from custom_components.magic_areas.const import (
    AREA_STATE_BRIGHT,
    AREA_STATE_CLEAR,
    AREA_STATE_DARK,
    AREA_STATE_EXTENDED,
    AREA_STATE_OCCUPIED,
    AREA_STATE_SLEEP,
    ATTR_ACTIVE_AREAS,
    ATTR_ACTIVE_SENSORS,
    ATTR_LAST_ACTIVE_SENSORS,
    ATTR_AREAS,
    ATTR_CLEAR_TIMEOUT,
    ATTR_FEATURES,
    ATTR_ON_STATES,
    ATTR_PRESENCE_SENSORS,
    ATTR_STATES,
    ATTR_TYPE,
    ATTR_UPDATE_INTERVAL,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONFIGURABLE_AREA_STATE_MAP,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_SLEEP_TIMEOUT,
    DISTRESS_SENSOR_CLASSES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    INVALID_STATES,
    AGGREGATE_MODE_ALL,
)
from custom_components.magic_areas.util import add_entities_when_ready

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)

def add_sensors(area, async_add_entities):

    # Create basic presence sensor
    async_add_entities([AreaPresenceBinarySensor(area)])

    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        create_aggregate_sensors(area, async_add_entities)

    if area.has_feature(CONF_FEATURE_HEALTH):
        create_health_sensors(area, async_add_entities)

def create_health_sensors(area, async_add_entities):
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return

    if BINARY_SENSOR_DOMAIN not in area.entities.keys():
        return

    distress_entities = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity.keys():
            continue

        if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES
    ):
        return

    _LOGGER.debug(f"Creating health sensor for area ({area.slug})")
    async_add_entities([AreaDistressBinarySensor(area)])


def create_aggregate_sensors(area, async_add_entities):
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in area.entities.keys():
        return

    device_class_count = {}

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if not ATTR_DEVICE_CLASS in entity.keys():
            continue

        if entity[ATTR_DEVICE_CLASS] not in device_class_count.keys():
            device_class_count[entity[ATTR_DEVICE_CLASS]] = 0

        device_class_count[entity[ATTR_DEVICE_CLASS]] += 1

    for device_class, entity_count in device_class_count.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES
        ):
            continue

        _LOGGER.debug(
            f"Creating aggregate sensor for device_class '{device_class}' with {entity_count} entities ({area.slug})"
        )
        aggregates.append(AreaSensorGroupBinarySensor(area, device_class))

    async_add_entities(aggregates)


class AreaPresenceBinarySensor(BinarySensorBase):
    """
        Setup & Teardown
    """
    def __init__(self, area):
        """Initialize the area presence binary sensor."""

        super().__init__(area, BinarySensorDeviceClass.OCCUPANCY)

        self._name = f"Area ({self.area.name})"

        self.last_off_time = datetime.utcnow()
        self.clear_timeout_callback = None

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self.area.config.get(CONF_ICON):
            return self.area.config.get(CONF_ICON)
        return None

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self.area.has_state(AREA_STATE_OCCUPIED)

    async def restore_state(self):

        last_state = await self.async_get_last_state()
        is_new_entry = last_state is None  # newly added to HA

        if is_new_entry:
            self.logger.debug(f"New sensor created: {self.name}")
            self.update_state()
        else:
            _LOGGER.debug(f"Sensor {self.name} restored [state={last_state.state}]")
            if ATTR_STATES in last_state.attributes.keys():
                self.area.states = last_state.attributes[ATTR_STATES]
            else:
                self.area.states = []
            self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        self.logger.debug(f"{self.name} Sensor initializing.")

        self.load_presence_sensors()
        self.load_attributes()

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug(f"{self.name} Sensor initialized.")

    async def _setup_listeners(self, _=None) -> None:
        self.logger.debug("%s: Called '_setup_listeners'", self.name)
        if not self.hass.is_running:
            self.logger.debug("%s: Cancelled '_setup_listeners'", self.name)
            return

        # Track presence sensors
        assert self.hass
        self.async_on_remove(
            async_track_state_change(self.hass, self.sensors, self.sensor_state_change)
        )

        # Track secondary states
        for configurable_state in self.get_configured_secondary_states():
            (
                configurable_state_entity,
                configurable_state_value,
            ) = CONFIGURABLE_AREA_STATE_MAP[configurable_state]
            tracked_entity = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                configurable_state_entity, None
            )

            if not tracked_entity:
                continue

            self.logger.debug(f"Secondary state tracking: {tracked_entity}")

            self.async_on_remove(
                async_track_state_change(
                    self.hass, tracked_entity, self.secondary_state_change
                )
            )

        # Timed self update
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))
        self.async_on_remove(
            async_track_time_interval(self.hass, self.refresh_states, delta)
        )

    def load_presence_sensors(self) -> None:
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
                    if ATTR_DEVICE_CLASS not in entity.keys():
                        continue

                    if entity[ATTR_DEVICE_CLASS] not in self.area.config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS):
                        continue

                self.sensors.append(entity[ATTR_ENTITY_ID])

        # Append presence_hold switch as a presence_sensor
        if self.area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
            )
            self.sensors.append(presence_hold_switch_id)

    def load_attributes(self) -> None:
        # Set attributes
        self._attributes = {}

        if not self.area.is_meta():
            self._attributes.update({ATTR_STATES: self.get_area_states()})
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

    def update_attributes(self):
        self._attributes[ATTR_STATES] = self.area.states
        self._attributes[ATTR_CLEAR_TIMEOUT] = self.get_clear_timeout()

        if self.area.is_meta():
            self._attributes[ATTR_ACTIVE_AREAS] = self.area.get_active_areas()


    """
        State Change Handling
    """

    def get_area_states(self):
        states = []

        # Get Main occupancy state
        current_state = self.get_occupancy_state()
        last_state = self.area.is_occupied()

        states.append(AREA_STATE_OCCUPIED if current_state else AREA_STATE_CLEAR)
        if current_state != last_state:
            self.area.last_changed = datetime.utcnow()
            self.logger.debug(
                f"{self.area.name}: State changed to {current_state} at {self.area.last_changed}"
            )

        seconds_since_last_change = (
            datetime.utcnow() - self.area.last_changed
        ).total_seconds()

        extended_time = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
            CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME
        )

        if AREA_STATE_OCCUPIED in states and seconds_since_last_change >= extended_time:
            states.append(AREA_STATE_EXTENDED)

        configurable_states = self.get_configured_secondary_states()

        # Assume AREA_STATE_DARK if not configured
        if AREA_STATE_DARK not in configurable_states:
            states.append(AREA_STATE_DARK)

        for configurable_state in configurable_states:
            (
                configurable_state_entity,
                configurable_state_value,
            ) = CONFIGURABLE_AREA_STATE_MAP[configurable_state]

            secondary_state_entity = self.area.config.get(
                CONF_SECONDARY_STATES, {}
            ).get(configurable_state_entity, None)
            secondary_state_value = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                configurable_state_value, None
            )

            if not secondary_state_entity:
                continue

            entity = self.hass.states.get(secondary_state_entity)

            if entity.state.lower() == secondary_state_value.lower():
                self.logger.debug(
                    f"{self.area.name}: Secondary state: {secondary_state_entity} is at {secondary_state_value}, adding {configurable_state}"
                )
                states.append(configurable_state)

        # Meta-state bright
        if AREA_STATE_DARK in configurable_states and AREA_STATE_DARK not in states:
            states.append(AREA_STATE_BRIGHT)

        return states

    def update_area_states(self):
        last_state = set(self.area.states.copy())
        # self.update_state()
        current_state = set(self.get_area_states())

        if last_state == current_state:
            return ([], [])

        # Calculate what's new
        new_states = current_state - last_state
        lost_states = last_state - current_state
        self.logger.debug(
            f"{self.name}: Current state: {current_state}, last state: {last_state} -> new states {new_states} / lost states {lost_states}"
        )

        self.area.states = list(current_state)

        return (new_states, lost_states)


    def get_occupancy_state(self):
        valid_on_states = (
            [STATE_ON] if self.area.is_meta() else self.area.config.get(CONF_ON_STATES)
        )
        area_state = self.get_sensors_state(valid_states=valid_on_states)

        if not area_state:
            if not self.area.is_occupied():
                return False

            if self.is_on_clear_timeout():
                self.logger.debug(f"{self.area.name}: Area is on timeout")
                if self.timeout_exceeded():
                    return False
            else:
                if self.area.is_occupied() and not area_state:
                    self.logger.debug(
                        f"{self.area.name}: Area not on timeout, setting call_later"
                    )
                    self.set_clear_timeout()
        else:
            self.remove_clear_timeout()

        return True

    def update_state(self):
        states_tuple = self.update_area_states()
        new_states, lost_states = states_tuple

        state_changed = any(
            state in new_states for state in [AREA_STATE_OCCUPIED, AREA_STATE_CLEAR]
        )

        self.logger.debug(
            f"{self.area.name}: States updated. New states: {new_states} / Lost states: {lost_states}"
        )

        self.update_attributes()
        self.schedule_update_ha_state()

        if state_changed:
            # Consider all secondary states new
            states_tuple = (self.area.states.copy(), [])

        self.report_state_change(states_tuple)

    def report_state_change(self, states_tuple=([], [])):
        new_states, lost_states = states_tuple
        self.logger.debug(
            f"Reporting state change for {self.area.name} (new states: {new_states}/lost states: {lost_states})"
        )
        dispatcher_send(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area.id, states_tuple
        )

    def secondary_state_change(self, entity_id, from_state, to_state):
        self.logger.debug(
            f"{self.name}: Secondary state change: entity '{entity_id}' changed to {to_state.state}"
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                f"{self.name}: sensor '{entity_id}' has invalid state {to_state.state}"
            )
            return None

        self.update_state()

    def get_configured_secondary_states(self):
        secondary_states = []

        for (
            configurable_state,
            configurable_state_opts,
        ) in CONFIGURABLE_AREA_STATE_MAP.items():
            (
                configurable_state_entity,
                configurable_state_value,
            ) = configurable_state_opts

            secondary_state_entity = self.area.config.get(
                CONF_SECONDARY_STATES, {}
            ).get(configurable_state_entity, None)

            if not secondary_state_entity:
                continue

            secondary_states.append(configurable_state)

        return secondary_states

    """
        Clearing
    """
    def get_clear_timeout(self):
        if self.area.has_state(AREA_STATE_SLEEP):
            return self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                CONF_SLEEP_TIMEOUT, DEFAULT_SLEEP_TIMEOUT
            )

        if self.area.has_state(AREA_STATE_EXTENDED):
            return self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                CONF_EXTENDED_TIMEOUT, DEFAULT_EXTENDED_TIMEOUT
            )

        return self.area.config.get(CONF_CLEAR_TIMEOUT)

    def set_clear_timeout(self):
        if not self.area.is_occupied():
            return False

        timeout = self.get_clear_timeout()

        self.logger.debug(f"{self.area.name}: Scheduling clear in {timeout} seconds")
        self.clear_timeout_callback = call_later(
            self.hass, timeout, self.refresh_states
        )

    def remove_clear_timeout(self):
        if not self.clear_timeout_callback:
            return False

        self.clear_timeout_callback()
        self.clear_timeout_callback = None

    def is_on_clear_timeout(self):
        return self.clear_timeout_callback is not None

    def timeout_exceeded(self):
        if not self.area.is_occupied():
            return False

        clear_delta = timedelta(seconds=self.get_clear_timeout())

        last_clear = self.last_off_time
        clear_time = last_clear + clear_delta
        time_now = datetime.utcnow()

        if time_now >= clear_time:
            self.logger.debug(f"{self.area.name}: Clear Timeout exceeded.")
            self.remove_clear_timeout()
            return True

        return False

class AreaSensorGroupBinarySensor(BinarySensorGroupBase):
    def __init__(self, area, device_class):
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, device_class)

        self._mode = "all" if device_class in AGGREGATE_MODE_ALL else "single"

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = f"Area {device_class_name} ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug(f"{self.name} Sensor initializing.")

        self.load_sensors(BINARY_SENSOR_DOMAIN)

        # Setup the listeners
        await self._setup_listeners()

        # Refresh state
        self.update_state()

        self.logger.debug(f"{self.name} Sensor initialized.")


class AreaDistressBinarySensor(BinarySensorGroupBase):
    def __init__(self, area):
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, BinarySensorDeviceClass.PROBLEM)

        self._name = f"Area Health ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug(f"{self.name} Sensor initializing.")

        self.load_sensors()

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug(f"{self.name} Sensor initialized.")

    def load_sensors(self):
        # Fetch sensors
        self.sensors = []

        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:
            if ATTR_DEVICE_CLASS not in entity.keys():
                continue

            if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
                continue

            self.sensors.append(entity["entity_id"])

        self._attributes = {"sensors": self.sensors, "active_sensors": []}
