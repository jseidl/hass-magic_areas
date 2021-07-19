DEPENDENCIES = ["magic_areas", "media_player", "binary_sensor"]

import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PROBLEM,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
    call_later,
)

from .base import AggregateBase, BinarySensorBase
from .const import (
    AREA_STATE_BRIGHT,
    AREA_STATE_DARK,
    AREA_STATE_EXTENDED,
    AREA_STATE_SLEEP,
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
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONFIGURABLE_AREA_STATE_MAP,
    DATA_AREA_OBJECT,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DEFAULT_SLEEP_TIMEOUT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    DISTRESS_SENSOR_CLASSES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""
    # await async_setup_platform(hass, {}, async_add_entities)
    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    await load_sensors(hass, async_add_entities, area)


async def load_sensors(hass, async_add_entities, area):

    # Create basic presence sensor
    async_add_entities([AreaPresenceBinarySensor(hass, area)])

    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        await create_aggregate_sensors(hass, area, async_add_entities)

    if area.has_feature(CONF_FEATURE_HEALTH):
        await create_health_sensors(hass, area, async_add_entities)


async def create_health_sensors(hass, area, async_add_entities):

    if not area.has_feature(CONF_FEATURE_HEALTH):
        return

    if BINARY_SENSOR_DOMAIN not in area.entities.keys():
        return

    distress_entities = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:

        if "device_class" not in entity.keys():
            continue

        if entity["device_class"] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES
    ):
        return

    _LOGGER.debug(f"Creating helth sensor for area ({area.slug})")
    async_add_entities([AreaDistressBinarySensor(hass, area)])


async def create_aggregate_sensors(hass, area, async_add_entities):

    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in area.entities.keys():
        return

    device_class_count = {}

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if not "device_class" in entity.keys():
            continue

        if entity["device_class"] not in device_class_count.keys():
            device_class_count[entity["device_class"]] = 0

        device_class_count[entity["device_class"]] += 1

    for device_class, entity_count in device_class_count.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES
        ):
            continue

        _LOGGER.debug(
            f"Creating aggregate sensor for device_class '{device_class}' with {entity_count} entities ({area.slug})"
        )
        aggregates.append(AreaSensorGroupBinarySensor(hass, area, device_class))

    async_add_entities(aggregates)


class AreaPresenceBinarySensor(BinarySensorBase):
    def __init__(self, hass, area):
        """Initialize the area presence binary sensor."""

        self.area = area
        self.hass = hass
        self._name = f"Area ({self.area.name})"
        self.area.occupied = False
        self.last_off_time = datetime.utcnow()
        self.clear_timeout_callback = None

        self._device_class = DEVICE_CLASS_OCCUPANCY
        self.sensors = []

    def load_presence_sensors(self) -> None:

        if self.area.is_meta():
            # MetaAreas track their children
            child_areas = self.area.get_child_areas()
            for child_area in child_areas:
                entity_id = f"binary_sensor.area_{child_area}"
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

                if (
                    component == BINARY_SENSOR_DOMAIN
                    and "device_class" in entity.keys()
                    and entity["device_class"]
                    not in self.area.config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS)
                ):
                    continue

                self.sensors.append(entity["entity_id"])

        # Append presence_hold switch as a presence_sensor
        if self.area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
            )
            self.sensors.append(presence_hold_switch_id)

    def load_attributes(self) -> None:

        # Set attributes
        self._attributes = {
            "presence_sensors": self.sensors,
            "features": [
                feature_name
                for feature_name, opts in self.area.config.get(
                    CONF_ENABLED_FEATURES, {}
                ).items()
            ],
            "active_sensors": [],
            "clear_timeout": self.area.config.get(CONF_CLEAR_TIMEOUT),
            "update_interval": self.area.config.get(CONF_UPDATE_INTERVAL),
            "type": self.area.config.get(CONF_TYPE),
        }

        if self.area.is_meta():
            self._attributes.update(
                {
                    "areas": self.area.get_child_areas(),
                    "active_areas": self.area.get_active_areas(),
                }
            )
            return

        # Add non-meta attributes
        self._attributes.update(
            {
                "on_states": self.area.config.get(CONF_ON_STATES),
                "secondary_states": self._get_secondary_states(),
            }
        )

        # Set attribute sleep_timeout if defined
        if self.area.config.get(CONF_SLEEP_TIMEOUT):
            self._attributes["sleep_timeout"] = self.area.config.get(CONF_SLEEP_TIMEOUT)

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self.area.config.get(CONF_ICON):
            return self.area.config.get(CONF_ICON)
        return None

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self.area.occupied

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._initialize()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._initialize
            )

        last_state = await self.async_get_last_state()
        is_new_entry = last_state is None  # newly added to HA

        if is_new_entry:
            _LOGGER.debug(f"New sensor created: {self.name}")
            self._update_state()
        else:
            _LOGGER.debug(f"Sensor {self.name} restored [state={last_state.state}]")
            self.area.occupied = last_state.state == STATE_ON
            self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:

        _LOGGER.debug(f"{self.name} Sensor initializing.")

        self.load_presence_sensors()
        self.load_attributes()

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug(f"{self.name} Sensor initialized.")

    async def _setup_listeners(self, _=None) -> None:
        _LOGGER.debug("%s: Called '_setup_listeners'", self.name)
        if not self.hass.is_running:
            _LOGGER.debug("%s: Cancelled '_setup_listeners'", self.name)
            return

        # Track presence sensors
        assert self.hass
        self.async_on_remove(
            async_track_state_change(self.hass, self.sensors, self.sensor_state_change)
        )

        # Track secondary states
        for configurable_state in self._get_configured_secondary_states():

            (
                configurable_state_entity,
                configurable_state_value,
            ) = CONFIGURABLE_AREA_STATE_MAP[configurable_state]
            tracked_entity = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
                configurable_state_entity, None
            )

            if not tracked_entity:
                continue

            _LOGGER.debug(f"Secondary state tracking: {tracked_entity}")

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

    def secondary_state_change(self, entity_id, from_state, to_state):

        _LOGGER.debug(
            f"{self.name}: Secondary state change: entity '{entity_id}' changed to {to_state.state}"
        )
        self._update_state()

    def _update_secondary_states(self):

        last_state = set(self.area.secondary_states.copy())
        # self._update_state()
        current_state = set(self._get_secondary_states())

        if last_state == current_state:
            return ([], [])

        # Calculate what's new
        new_states = current_state - last_state
        lost_states = last_state - current_state
        _LOGGER.debug(
            f"{self.name}: Current state: {current_state}, last state: {last_state} -> new states {new_states} / lost states {lost_states}"
        )

        self.area.secondary_states = list(current_state)

        return (new_states, lost_states)

    def _get_configured_secondary_states(self):

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

    def _get_secondary_states(self):

        secondary_states = []

        seconds_since_last_change = (
            datetime.utcnow() - self.area.last_changed
        ).total_seconds()

        extended_time = self.area.config.get(CONF_SECONDARY_STATES, {}).get(
            CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME
        )

        if self.area.is_occupied() and seconds_since_last_change >= extended_time:
            secondary_states.append(AREA_STATE_EXTENDED)

        configurable_states = self._get_configured_secondary_states()

        # Assume AREA_STATE_DARK if not configured
        if AREA_STATE_DARK not in configurable_states:
            secondary_states.append(AREA_STATE_DARK)

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
                _LOGGER.debug(
                    f"{self.area.name}: Secondary state: {secondary_state_entity} is at {secondary_state_value}, adding {configurable_state}"
                )
                secondary_states.append(configurable_state)

        # Meta-state bright
        if (
            AREA_STATE_DARK in configurable_states
            and AREA_STATE_DARK not in secondary_states
        ):
            secondary_states.append(AREA_STATE_BRIGHT)

        return secondary_states

    def _update_attributes(self):

        self._attributes["secondary_states"] = self.area.secondary_states
        self._attributes["clear_timeout"] = self.get_clear_timeout()

        if self.area.is_meta():
            self._attributes["active_areas"] = self.area.get_active_areas()

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

        _LOGGER.debug(f"{self.area.name}: Scheduling clear in {timeout} seconds")
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
            _LOGGER.debug(f"{self.area.name}: Clear Timeout exceeded.")
            self.remove_clear_timeout()
            return True

        return False

    def _update_state(self):

        valid_on_states = (
            [STATE_ON] if self.area.is_meta() else self.area.config.get(CONF_ON_STATES)
        )

        area_state = self._get_sensors_state(valid_states=valid_on_states)
        last_state = self.area.occupied

        _LOGGER.warn(
            f"{self.area.name}: Current state: {area_state}, Last State: {last_state}, Valid on states: {valid_on_states}"
        )

        if area_state:
            self.area.occupied = True
            self.remove_clear_timeout()
        else:
            if self.is_on_clear_timeout():
                _LOGGER.warn(f"{self.area.name}: Area is on timeout")
                if self.timeout_exceeded():
                    self.area.occupied = False
            else:
                if self.area.is_occupied() and not area_state:
                    _LOGGER.warn(
                        f"{self.area.name}: Area not on timeout, setting call_later"
                    )
                    self.set_clear_timeout()

        state_changed = last_state != self.area.is_occupied()

        if state_changed:
            self.area.last_changed = datetime.utcnow()

        states_tuple = self._update_secondary_states()
        new_states, lost_states = states_tuple
        _LOGGER.debug(
            f"{self.area.name}: Secondary states updated. New states: {new_states} / Lost states: {lost_states}"
        )

        self._update_attributes()
        self.schedule_update_ha_state()

        if state_changed:
            # Consider all secondary states new
            states_tuple = (self.area.secondary_states.copy(), [])

        self.report_state_change(states_tuple)

    def report_state_change(self, states_tuple=([], [])):
        new_states, lost_states = states_tuple
        _LOGGER.debug(
            f"Reporting state change for {self.area.id} (new states: {new_states}/lost states: {lost_states})"
        )
        dispatcher_send(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area.id, states_tuple
        )


class AreaSensorGroupBinarySensor(BinarySensorBase, AggregateBase):
    def __init__(self, hass, area, device_class):
        """Initialize an area sensor group binary sensor."""

        self.area = area
        self.hass = hass
        self._device_class = device_class
        self._state = False

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = f"Area {device_class_name} ({self.area.name})"

    async def _initialize(self, _=None) -> None:

        _LOGGER.debug(f"{self.name} Sensor initializing.")

        self.load_sensors(BINARY_SENSOR_DOMAIN)

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug(f"{self.name} Sensor initialized.")


class AreaDistressBinarySensor(BinarySensorBase, AggregateBase):
    def __init__(self, hass, area):
        """Initialize an area sensor group binary sensor."""

        self.area = area
        self.hass = hass
        self._device_class = DEVICE_CLASS_PROBLEM
        self._state = False

        self._name = f"Area Health ({self.area.name})"

    async def _initialize(self, _=None) -> None:

        _LOGGER.debug(f"{self.name} Sensor initializing.")

        self.load_sensors()

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug(f"{self.name} Sensor initialized.")

    def load_sensors(self):

        # Fetch sensors
        self.sensors = []

        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:

            if "device_class" not in entity.keys():
                continue

            if entity["device_class"] not in DISTRESS_SENSOR_CLASSES:
                continue

            self.sensors.append(entity["entity_id"])

        self._attributes = {"sensors": self.sensors, "active_sensors": []}
