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
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from .base import AggregateBase, BinarySensorBase
from .const import (
    AUTOLIGHTS_STATE_DISABLED,
    AUTOLIGHTS_STATE_NORMAL,
    AUTOLIGHTS_STATE_SLEEP,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_ENABLED_FEATURES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_CLIMATE_CONTROL,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_CONTROL,
    CONF_FEATURE_MEDIA_CONTROL,
    CONF_ICON,
    CONF_MAIN_LIGHTS,
    CONF_NIGHT_ENTITY,
    CONF_NIGHT_STATE,
    CONF_ON_STATES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_TIMEOUT,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    DATA_AREA_OBJECT,
    DISTRESS_SENSOR_CLASSES,
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

    if len(distress_entities) < area.config.get(CONF_AGGREGATES_MIN_ENTITIES):
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
        if entity_count < area.config.get(CONF_AGGREGATES_MIN_ENTITIES):
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
        self._state = False
        self.last_off_time = datetime.utcnow()

        self._device_class = DEVICE_CLASS_OCCUPANCY
        self.sensors = []

        self.tracking_listeners = []

    def load_presence_sensors(self) -> None:

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

        if not self.area.is_meta():
            # Append presence_hold switch as a presence_sensor
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
            )
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
            "features": self.area.config.get(CONF_ENABLED_FEATURES),
            "active_sensors": [],
            "lights": area_lights,
            "clear_timeout": self.area.config.get(CONF_CLEAR_TIMEOUT),
            "update_interval": self.area.config.get(CONF_UPDATE_INTERVAL),
            "type": self.area.config.get(CONF_TYPE),
        }

        if self.area.is_meta():
            return

        # Add non-meta attributes
        self._attributes.update(
            {
                "climate": area_climate,
                "on_states": self.area.config.get(CONF_ON_STATES),
                "automatic_lights": self._get_autolights_state(),
                "night": self.area.is_night(),
                "sleep": self.area.is_sleeping(),
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
            self._state = last_state.state == STATE_ON
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
        remove_presence = async_track_state_change(
            self.hass, self.sensors, self.sensor_state_change
        )

        # Track autolight_disable sensor if available
        if self.area.config.get(CONF_NIGHT_ENTITY):
            remove_disable = async_track_state_change(
                self.hass,
                self.area.config.get(CONF_NIGHT_ENTITY),
                self.autolight_disable_state_change,
            )
            self.tracking_listeners.append(remove_disable)

        # Track autolight_sleep sensor if available
        if self.area.config.get(CONF_SLEEP_ENTITY):
            remove_sleep = async_track_state_change(
                self.hass,
                self.area.config.get(CONF_SLEEP_ENTITY),
                self.autolight_sleep_state_change,
            )
            self.tracking_listeners.append(remove_sleep)

        # Timed self update
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))
        remove_interval = async_track_time_interval(
            self.hass, self.refresh_states, delta
        )

        self.tracking_listeners.extend([remove_presence, remove_interval])

    def autolight_sleep_state_change(self, entity_id, from_state, to_state):

        self._update_autolights_state()

    def autolight_disable_state_change(self, entity_id, from_state, to_state):

        last_state = self._attributes["automatic_lights"]
        self._update_autolights_state()

        # Check state change
        if self._attributes["automatic_lights"] != last_state:

            if not to_state:
                return

            if to_state.state != self.area.config.get(CONF_NIGHT_STATE):
                if self._state:
                    self._lights_off()
            else:
                if self._state:
                    self._lights_on()

    def _update_autolights_state(self):

        self._update_attributes()
        self.schedule_update_ha_state()

    def _is_autolights_disabled(self):

        if not self.area.config.get(CONF_NIGHT_ENTITY):
            return False

        return not self.area.is_night()

    def _get_autolights_state(self):

        if (
            not self.area.has_feature(CONF_FEATURE_LIGHT_CONTROL)
            or self._is_autolights_disabled()
        ):
            return AUTOLIGHTS_STATE_DISABLED

        if self.area.is_sleeping() and self.area.config.get(CONF_SLEEP_LIGHTS):
            return AUTOLIGHTS_STATE_SLEEP

        return AUTOLIGHTS_STATE_NORMAL

    def _autolights(self):

        # All lights affected by default
        affected_lights = [
            entity["entity_id"] for entity in self.area.entities[LIGHT_DOMAIN]
        ]

        # Regular operation
        if self.area.config.get(CONF_MAIN_LIGHTS):
            affected_lights = self.area.config.get(CONF_MAIN_LIGHTS)

        # Check if in disable mode
        if self._is_autolights_disabled():
            return False

        # Check if in sleep mode
        if self.area.is_sleeping() and self.area.config.get(CONF_SLEEP_LIGHTS):
            affected_lights = self.area.config.get(CONF_SLEEP_LIGHTS)

        # Call service to turn_on the lights
        service_data = {ATTR_ENTITY_ID: affected_lights}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _update_attributes(self):

        self._attributes["night"] = self.area.is_night()
        self._attributes["sleep"] = self.area.is_sleeping()
        self._attributes["automatic_lights"] = self._get_autolights_state()

    def _update_state(self):

        area_state = self._get_sensors_state()
        last_state = self._state
        sleep_timeout = self.area.config.get(CONF_SLEEP_TIMEOUT)

        if area_state:
            self._state = True
        else:
            if sleep_timeout and self.area.is_sleeping():
                # if in sleep mode and sleep_timeout is set, use it...
                _LOGGER.debug(
                    f"Area {self.area.slug} sleep mode is active. Timeout: {str(sleep_timeout)}"
                )
                clear_delta = timedelta(seconds=sleep_timeout)
            else:
                # ..else, use clear_timeout
                _LOGGER.debug(
                    f"Area {self.area.slug} ... Timeout: {str(self.area.config.get(CONF_CLEAR_TIMEOUT))}"
                )
                clear_delta = timedelta(
                    seconds=self.area.config.get(CONF_CLEAR_TIMEOUT)
                )

            last_clear = self.last_off_time
            clear_time = last_clear + clear_delta
            time_now = datetime.utcnow()

            if time_now >= clear_time:
                self._state = False

        self._update_attributes()
        self.schedule_update_ha_state()

        # Check state change
        if last_state != self._state:

            if self._state:
                self._state_on()
            else:
                self._state_off()

    def _get_sensors_state(self):

        active_sensors = []

        # Loop over all entities and check their state
        for sensor in self.sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.info(
                    f"Could not get sensor state: {sensor} entity not found, skipping"
                )
                continue

            # Skip unavailable entities
            if entity.state == STATE_UNAVAILABLE:
                continue

            if entity.state in self.area.config.get(CONF_ON_STATES):
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0

    def _lights_on(self):
        # Turn on lights, if configured
        if self.area.has_feature(CONF_FEATURE_LIGHT_CONTROL) and self.area.has_entities(
            LIGHT_DOMAIN
        ):
            self._autolights()

    def _state_on(self):

        self._lights_on()

        # Turn on climate, if configured
        if self.area.has_feature(
            CONF_FEATURE_CLIMATE_CONTROL
        ) and self.area.has_entities(CLIMATE_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity["entity_id"] for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_ON, service_data)

    def _lights_off(self):
        # Turn off lights, if configured
        if self.area.has_feature(CONF_FEATURE_LIGHT_CONTROL) and self.area.has_entities(
            LIGHT_DOMAIN
        ):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity["entity_id"] for entity in self.area.entities[LIGHT_DOMAIN]
                ]
            }
            self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

    def _state_off(self):

        self._lights_off()

        # Turn off climate, if configured
        if self.area.has_feature(
            CONF_FEATURE_CLIMATE_CONTROL
        ) and self.area.has_entities(CLIMATE_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity["entity_id"] for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_OFF, service_data)

        # Turn off media, if configured
        if self.area.has_feature(CONF_FEATURE_MEDIA_CONTROL) and self.area.has_entities(
            MEDIA_PLAYER_DOMAIN
        ):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity["entity_id"]
                    for entity in self.area.entities[MEDIA_PLAYER_DOMAIN]
                ]
            }
            self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)


class AreaSensorGroupBinarySensor(BinarySensorBase, AggregateBase):
    def __init__(self, hass, area, device_class):
        """Initialize an area sensor group binary sensor."""

        self.area = area
        self.hass = hass
        self._device_class = device_class
        self._state = False

        device_class_name = device_class.capitalize()
        self._name = f"Area {device_class_name} ({self.area.name})"

        self.tracking_listeners = []

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

        self.tracking_listeners = []

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
