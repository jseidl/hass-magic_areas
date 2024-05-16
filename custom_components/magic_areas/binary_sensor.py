"""Binary sensor control for magic areas."""

from datetime import datetime, timedelta, UTC
import logging

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.base.primitives import (
    BinarySensorBase,
    BinarySensorGroupBase,
)
from custom_components.magic_areas.const import (
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
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DISTRESS_SENSOR_CLASSES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    INVALID_STATES,
    AreaState,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    LightEntityConf,
)
from custom_components.magic_areas.util import add_entities_when_ready
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
    call_later,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the basic sensors for the area."""
    # Create basic presence sensor
    async_add_entities([AreaPresenceBinarySensor(area)])

    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        create_aggregate_sensors(area, async_add_entities)

    if area.has_feature(CONF_FEATURE_HEALTH):
        create_health_sensors(area, async_add_entities)


def create_health_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return

    distress_entities = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES
    ):
        return

    _LOGGER.debug("Creating health sensor for area (%s)", area.slug)
    async_add_entities([AreaDistressBinarySensor(area)])


def create_aggregate_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Create the aggregate sensors for the area."""
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in area.entities:
        return

    device_class_count = {}

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in device_class_count:
            device_class_count[entity[ATTR_DEVICE_CLASS]] = 0

        device_class_count[entity[ATTR_DEVICE_CLASS]] += 1

    for device_class, entity_count in device_class_count.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            entity_count,
            area.slug,
        )
        aggregates.append(AreaSensorGroupBinarySensor(area, device_class))

    async_add_entities(aggregates)


class AreaPresenceBinarySensor(BinarySensorBase):
    """Create an area presence binary sensor that tracks the current occupied state."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        super().__init__(area, BinarySensorDeviceClass.OCCUPANCY)

        self._name = f"Area ({self.area.name})"

        self.last_off_time = datetime.now(UTC)
        self._clear_timeout_callback = None
        self.attributes = {}

    @property
    def icon(self) -> str | None:
        """Return the icon to be used for this entity."""
        if self.area.config.get(CONF_ICON):
            return self.area.config.get(CONF_ICON)
        return None

    @property
    def is_on(self) -> bool:
        """Return true if the area is occupied."""
        return self.area.is_occupied()

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
            async_track_state_change(self.hass, self.sensors, self.sensor_state_change)
        )

        # Track secondary states
        for conf in ALL_LIGHT_ENTITIES:
            if not conf.has_entity:
                continue

            tracked_entity = self.area.config.get(conf.entity_name(), None)

            if not tracked_entity:
                continue

            self.logger.debug("Secondary state tracking: %s", tracked_entity)

            self.async_on_remove(
                async_track_state_change(
                    self.hass, tracked_entity, self._secondary_state_change
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

        # Append presence_hold switch as a presence_sensor
        if self.area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
            )
            self.sensors.append(presence_hold_switch_id)

    def _load_attributes(self) -> None:
        # Set attributes
        self.attributes = {}

        if not self.area.is_meta():
            self.attributes.update({ATTR_STATE: self.area.state})
        else:
            self.attributes.update(
                {
                    ATTR_AREAS: self.area.get_child_areas(),
                    ATTR_ACTIVE_AREAS: self.area.get_active_areas(),
                }
            )

        # Add common attributes
        self.attributes.update(
            {
                ATTR_ACTIVE_SENSORS: [],
                ATTR_LAST_ACTIVE_SENSORS: [],
                ATTR_PRESENCE_SENSORS: self.sensors,
                ATTR_TYPE: self.area.config.get(CONF_TYPE),
            }
        )

    def _update_attributes(self):
        self.attributes[ATTR_STATE] = self.area.state
        self.attributes[ATTR_CLEAR_TIMEOUT] = self._get_clear_timeout()

        if self.area.is_meta():
            self.attributes[ATTR_ACTIVE_AREAS] = self.area.get_active_areas()

    ####
    ####     State Change Handling
    def get_current_area_state(self) -> AreaState:
        """Get the current state for the area based on the various entities and controls."""
        # Get Main occupancy state
        occupied_state = self._get_occupancy_state()

        seconds_since_last_change = (
            datetime.now(UTC) - self.area.last_changed
        ).total_seconds()

        conf = self.area.state_config(AreaState.AREA_STATE_EXTENDED)
        extended_time = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
            conf.state_timeout(), conf.timeout
        )

        if not occupied_state:
            if seconds_since_last_change >= extended_time:
                return AreaState.AREA_STATE_EXTENDED
            return AreaState.AREA_STATE_CLEAR

        # If it is not occupied, then set the override state or leave as just occupied.
        state = AreaState.AREA_STATE_OCCUPIED

        for conf in ALL_LIGHT_ENTITIES:
            if not conf.has_entity:
                continue

            secondary_state_entity = self.area.config.get(conf.entity_name(), None)
            secondary_state_value = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                conf.state_name(), None
            )

            if not secondary_state_entity:
                continue

            entity = self.hass.states.get(secondary_state_entity)

            if entity.state.lower() == secondary_state_value.lower():
                self.logger.debug(
                    "%s: Secondary state: %s is at %s, adding %s",
                    self.area.name,
                    secondary_state_entity,
                    secondary_state_value,
                    conf.enable_state,
                )
                state = conf.enable_state

        return state

    def _update_area_states(self) -> tuple[AreaState, AreaState]:
        """Update the state for the areas."""
        last_state = self.area.state
        current_state = self.get_current_area_state()

        if last_state == current_state:
            return None

        # Calculate what's new
        self.logger.debug(
            "%s: Current state: %s, last state: %s",
            self.name,
            current_state,
            last_state,
        )

        return (current_state, last_state)

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
                if self.timeout_exceeded():
                    return False
            elif self.area.is_occupied() and not area_state:
                self.logger.debug(
                    "%s: Area not on timeout, setting call_later", self.area.name
                )
                self._set_clear_timeout()
        else:
            self._remove_clear_timeout()

        return True

    def _update_state(self):
        states_tuple = self._update_area_states()
        new_states, lost_states = states_tuple

        self.logger.debug(
            "%s: States updated. New states: %s / Lost states: %s",
            self.area.name,
            new_states,
            lost_states,
        )

        self._update_attributes()
        self.schedule_update_ha_state()

        self._report_state_change(states_tuple)

    def _report_state_change(self, states_tuple: tuple[AreaState, AreaState]):
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

    def _secondary_state_change(self, entity_id, from_state, to_state):
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
        conf = self.area.state_config()
        if conf.has_entity:
            return self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                conf.state_timeout(), conf.timeout
            )

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


class AreaSensorGroupBinarySensor(BinarySensorGroupBase):
    """Group binary sensor for the area."""

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, device_class)

        self._mode = "all" if device_class in AGGREGATE_MODE_ALL else "single"

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = f"Area {device_class_name} ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing.", self.name)

        self.load_sensors(BINARY_SENSOR_DOMAIN)

        # Setup the listeners
        await self._setup_listeners()

        # Refresh state
        self._update_state()

        self.logger.debug("%s Sensor initialized.", self.name)


class AreaDistressBinarySensor(BinarySensorGroupBase):
    """The distress binary sensor for the area."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, BinarySensorDeviceClass.PROBLEM)

        self._name = f"Area Health ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing.", self.name)

        self.load_sensors()

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug("%s Sensor initialized.", self.name)

    def load_sensors(self) -> None:
        """Load the sensors from the system."""
        # Fetch sensors
        self.sensors = []

        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:
            if ATTR_DEVICE_CLASS not in entity:
                continue

            if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
                continue

            self.sensors.append(entity["entity_id"])

        self.attributes = {"sensors": self.sensors, "active_sensors": []}
