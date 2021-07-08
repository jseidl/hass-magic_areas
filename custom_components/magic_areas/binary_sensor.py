DEPENDENCIES = ["magic_areas", "media_player", "binary_sensor"]

import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PROBLEM,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
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
)

from .base import AggregateBase, BinarySensorBase
from .const import (
    AREA_STATE_EXTENDED,
    CONF_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIME,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_DARK_ENTITY,
    CONF_DARK_STATE,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_OVERHEAD_LIGHTS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONFIGURABLE_AREA_STATE_MAP,
    DATA_AREA_OBJECT,
    DISTRESS_SENSOR_CLASSES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    META_AREAS,
    MODULE_DATA,
    PRESENCE_DEVICE_COMPONENTS,
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

        for component, entities in self.area.entities.items():

            if component not in PRESENCE_DEVICE_COMPONENTS:
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
        presence_hold_switch_id = f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
        self.sensors.append(presence_hold_switch_id)

    def load_attributes(self) -> None:

        area_lights = (
            [entity["entity_id"] for entity in self.area.entities[LIGHT_DOMAIN]]
            if self.area.has_entities(LIGHT_DOMAIN)
            else []
        )

        area_climate = (
            [entity["entity_id"] for entity in self.area.entities[CLIMATE_DOMAIN]]
            if self.area.has_entities(CLIMATE_DOMAIN)
            else []
        )

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
            "lights": area_lights,
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
                "climate": area_climate,
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
            return []

        # Calculate what's new
        new_states = current_state - last_state
        _LOGGER.debug(
            f"{self.name}: Current state: {current_state}, last state: {last_state} -> new states {new_states}"
        )

        self.area.secondary_states = list(current_state)

        return new_states

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

        extended_time = self.area.config.get(
                CONF_SECONDARY_STATES, {}
            ).get(CONF_EXTENDED_TIME, DEFAULT_EXTENDED_TIME)

        if self.area.is_occupied() and seconds_since_last_change >= extended_time:
            secondary_states.append(AREA_STATE_EXTENDED)

        for configurable_state in self._get_configured_secondary_states():

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

        return secondary_states

    def _update_attributes(self):

        self._attributes["secondary_states"] = self.area.secondary_states

        if self.area.is_meta():
            self._attributes["active_areas"] = self.area.get_active_areas()

    def _update_state(self):

        valid_on_states = (
            [STATE_ON] if self.area.is_meta() else self.area.config.get(CONF_ON_STATES)
        )

        area_state = self._get_sensors_state(valid_states=valid_on_states)
        last_state = (self.area.occupied)
        sleep_timeout = self.area.config.get(CONF_SLEEP_TIMEOUT)

        _LOGGER.warn(f"{self.area.name}: Current state: {area_state}, Last State: {last_state}, Valid on states: {valid_on_states}")

        if area_state:
            _LOGGER.debug(f"Area {self.area.slug} state: Occupancy detected.")
            self.area.occupied = True
        else:
            _LOGGER.debug(f"Area {self.area.slug} state: Occupancy not detected.")
            if sleep_timeout and self.area.is_sleeping():
                # if in sleep mode and sleep_timeout is set, use it...
                _LOGGER.debug(
                    f"Area {self.area.slug} sleep mode is active. Timeout: {str(sleep_timeout)}"
                )
                clear_delta = timedelta(seconds=sleep_timeout)
            else:
                # ..else, use clear_timeout
                _LOGGER.debug(
                    f"Area {self.area.slug} not in sleep mode. Timeout: {str(self.area.config.get(CONF_CLEAR_TIMEOUT))}"
                )
                clear_delta = timedelta(
                    seconds=self.area.config.get(CONF_CLEAR_TIMEOUT)
                )

            last_clear = self.last_off_time
            clear_time = last_clear + clear_delta
            time_now = datetime.utcnow()

            if time_now >= clear_time:
                _LOGGER.debug(
                    f"Area {self.area.slug} timeout exceeded. Clearing occupancy state."
                )
                self.area.occupied = False

        state_changed = last_state != self.area.occupied

        new_states = self._update_secondary_states()
        _LOGGER.debug(f"Secondary states updated. New states: {new_states}")        
        
        self.area.last_changed = datetime.utcnow()

        self._update_attributes()
        self.schedule_update_ha_state()

        if state_changed:
            # Consider all secondary states new
            new_states = self.area.secondary_states.copy()
        self.report_state_change(new_states)

    def report_state_change(self, new_states=[]):
        _LOGGER.debug(
            f"Reporting state change for {self.area.id} (new states: {new_states})"
        )
        dispatcher_send(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area.id, new_states
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
