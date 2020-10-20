DEPENDENCIES = ["magic_areas", "media_player", "binary_sensor"]

import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_GAS,
    DEVICE_CLASS_LIGHT,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_WINDOW,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_START,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ALARM_TRIGGERED,
    STATE_HOME,
    STATE_OFF,
    STATE_ON,
    STATE_PROBLEM,
)
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from . import (
    CONF_AL_DISABLE_ENTITY,
    CONF_AL_DISABLE_STATE,
    CONF_AL_ENTITIES,
    CONF_AL_SLEEP_ENTITY,
    CONF_AL_SLEEP_LIGHTS,
    CONF_AL_SLEEP_STATE,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

PRESENCE_DEVICE_COMPONENTS = [
    MEDIA_PLAYER_DOMAIN,
    BINARY_SENSOR_DOMAIN,
]  # @todo make configurable
AGGREGATE_SENSOR_CLASSES = [
    DEVICE_CLASS_WINDOW,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_LIGHT,
]

DISTRESS_SENSOR_CLASSES = [
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_GAS,
]  # @todo make configurable
DISTRESS_STATES = [STATE_ALARM_TRIGGERED, STATE_ON, STATE_PROBLEM]


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument

    areas = hass.data.get(MODULE_DATA)

    distress_sensors = []
    aggregate_sensors = []

    # Create basic presence sensors
    async_add_entities([AreaPresenceBinarySensor(hass, area) for area in areas])

    device_class_area_map = {}

    # Create distress sensors
    for area in areas:

        if BINARY_SENSOR_DOMAIN not in area.entities.keys():
            continue

        for sensor in area.entities[BINARY_SENSOR_DOMAIN]:
            if sensor.device_class not in DISTRESS_SENSOR_CLASSES:
                continue

            _LOGGER.info(f"Creating distress binary_sensor for {area.name}")
            distress_sensors.append(AreaDistressBinarySensor(hass, area))
            break  # back to area loop

        # Create Aggregate Sensors
        available_device_classes = []

        # binary_sensor Aggregates
        if BINARY_SENSOR_DOMAIN not in area.entities.keys():
            continue

        for sensor in area.entities[BINARY_SENSOR_DOMAIN]:

            if sensor.device_class not in AGGREGATE_SENSOR_CLASSES:
                continue

            available_device_classes.append(sensor.device_class)

        for device_class in set(available_device_classes):

            if device_class not in device_class_area_map.keys():
                device_class_area_map[device_class] = {"exterior": [], "interior": []}

            area_location = "exterior" if area.exterior else "interior"
            device_class_area_map[device_class][area_location].append(area)

            _LOGGER.info(
                f"Creating aggregate binary_sensor for {area.name}/{device_class}"
            )
            aggregate_sensors.append(
                AreaSensorGroupBinarySensor(hass, area, device_class)
            )

    # Add all extra entities
    extra_entities = distress_sensors + aggregate_sensors
    if extra_entities:
        async_add_entities(extra_entities)

    # Add Global Aggregates
    global_aggregates = []
    for device_class, locations in device_class_area_map.items():
        for location_name, areas in locations.items():
            if areas:
                global_aggregates.append(
                    GlobalSensorGroupBinarySensor(
                        hass, areas, device_class, location_name
                    )
                )

    if global_aggregates:
        async_add_entities(global_aggregates)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class AreaPresenceBinarySensor(BinarySensorEntity):
    def __init__(self, hass, area):
        """Initialize the area presence binary sensor."""

        self.area = area
        self.hass = hass
        self._name = f"Area ({self.area.name})"
        self._state = None
        self.last_off_time = datetime.utcnow()

        self._passive = self.area.passive_start  # Prevent acting until all is loaded

        _LOGGER.info(f"Area {self.area.slug} presence sensor initializing.")

        # Fetch presence sensors
        self.presence_sensors = []
        for component, entities in self.area.entities.items():

            if component not in PRESENCE_DEVICE_COMPONENTS:
                continue

            for entity in entities:

                if (
                    component == BINARY_SENSOR_DOMAIN
                    and entity.device_class not in self.area.presence_device_class
                ):
                    continue

                self.presence_sensors.append(entity.entity_id)

        # Append presence_hold switch as a presence_sensor
        presence_hold_switch_id = f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
        self.presence_sensors.append(presence_hold_switch_id)

        area_lights = (
            [entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]]
            if LIGHT_DOMAIN in self.area.entities.keys()
            else []
        )
        area_climate = (
            [entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]]
            if CLIMATE_DOMAIN in self.area.entities.keys()
            else []
        )

        # Set attributes
        self._attributes = {
            "presence_sensors": self.presence_sensors,
            "active_sensors": [],
            "lights": area_lights,
            "climate": area_climate,
            "clear_timeout": self.area.clear_timeout,
            "update_interval": self.area.update_interval,
            "on_states": self.area.on_states,
            "exterior": self.area.exterior,
        }

        # Track presence sensors
        async_track_state_change(hass, self.presence_sensors, self.sensor_state_change)

        # Track autolight_disable sensor if available
        if self.area.automatic_lights[CONF_AL_DISABLE_ENTITY]:
            async_track_state_change(
                hass,
                self.area.automatic_lights[CONF_AL_DISABLE_ENTITY],
                self.autolight_disable_state_change,
            )

        # Timed self update
        delta = timedelta(seconds=self.area.update_interval)
        async_track_time_interval(self.hass, self.update_area, delta)

        _LOGGER.info(f"Area {self.area.slug} presence sensor initialized.")

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self.area.icon is not None:
            return self.area.icon
        return None

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return DEVICE_CLASS_OCCUPANCY

    def autolight_disable_state_change(self, entity_id, from_state, to_state):

        if self._passive:
            return

        if to_state.state == STATE_OFF:
            if self._state:
                self._lights_on()
        else:
            self._lights_off()

    def sensor_state_change(self, entity_id, from_state, to_state):
        if to_state.state not in self.area.on_states:
            self.last_off_time = datetime.utcnow()  # Update last_off_time

        return self._update_state()

    def update_area(self, next_interval):
        return self._update_state()

    def _autolights(self):

        # All lights affected by default
        affected_lights = [
            entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]
        ]

        # Regular operation
        if self.area.automatic_lights[CONF_AL_ENTITIES]:
            affected_lights = self.area.automatic_lights[CONF_AL_ENTITIES]

        # Check if disabled
        if self.area.automatic_lights[CONF_AL_DISABLE_ENTITY]:
            disable_entity = self.hass.states.get(
                self.area.automatic_lights[CONF_AL_DISABLE_ENTITY]
            )
            if (
                disable_entity.state.lower()
                == self.area.automatic_lights[CONF_AL_DISABLE_STATE].lower()
            ):
                _LOGGER.info(
                    f"Disable entity '{disable_entity.entity_id}' on disable state '{disable_entity.state}'"
                )
                return False

        # Check if in sleep mode
        if self.area.automatic_lights[CONF_AL_SLEEP_ENTITY]:
            if not self.area.automatic_lights[CONF_AL_SLEEP_LIGHTS]:
                # If user fails to set CONF_AL_SLEEP_LIGHTS, sleep mode will be ignored
                _LOGGER.error(
                    f"'{CONF_AL_SLEEP_LIGHTS}' not defined. Please review your configuration."
                )
            else:
                sleep_entity = self.hass.states.get(
                    self.area.automatic_lights[CONF_AL_SLEEP_ENTITY]
                )
                if (
                    sleep_entity.state.lower()
                    == self.area.automatic_lights[CONF_AL_SLEEP_STATE].lower()
                ):
                    _LOGGER.info(
                        f"Sleep entity '{sleep_entity.entity_id}' on sleep state '{sleep_entity.state}'"
                    )
                    affected_lights = self.area.automatic_lights[CONF_AL_SLEEP_LIGHTS]

        # Call service to turn_on the lights
        service_data = {ATTR_ENTITY_ID: affected_lights}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _update_state(self):

        area_state = self._get_area_state()
        last_state = self._state

        if area_state:
            self._state = True
        else:
            clear_delta = timedelta(seconds=self.area.clear_timeout)
            last_clear = self.last_off_time
            clear_time = last_clear + clear_delta
            time_now = datetime.utcnow()

            if time_now >= clear_time:
                self._state = False

        self.schedule_update_ha_state()

        # Check state change
        if last_state != self._state:

            # Skip first state change to STATE_ON
            if self._passive and self._state:
                _LOGGER.info(f"{self.area.name} is on passive mode.")
                self._passive = False
                return

            if self._state:
                self._state_on()
            else:
                self._state_off()

    def _has_entities(self, domain):

        return domain in self.area.entities.keys()

    def _lights_on(self):
        # Turn on lights, if configured
        if self.area.control_lights and self._has_entities(LIGHT_DOMAIN):
            self._autolights()

    def _state_on(self):

        self._lights_on()

        # Turn on climate, if configured
        if self.area.control_climate and self._has_entities(CLIMATE_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_ON, service_data)

    def _lights_off(self):
        # Turn off lights, if configured
        if self.area.control_lights and self._has_entities(LIGHT_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]
                ]
            }
            self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

    def _state_off(self):

        self._lights_off()

        # Turn off climate, if configured
        if self.area.control_climate and self._has_entities(CLIMATE_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_OFF, service_data)

        # Turn off media, if configured
        if self.area.control_media and self._has_entities(MEDIA_PLAYER_DOMAIN):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id
                    for entity in self.area.entities[MEDIA_PLAYER_DOMAIN]
                ]
            }
            self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)

    def _get_area_state(self):

        active_sensors = []

        # Loop over all entities and check their state
        for sensor in self.presence_sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.info(
                    f"Could not get sensor state: {sensor} entity not found, skipping"
                )
                continue

            if entity.state in self.area.on_states:
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0


class AreaDistressBinarySensor(BinarySensorEntity):
    def __init__(self, hass, area):
        """Initialize the area distress binary sensor."""

        self.area = area
        self.hass = hass
        self._name = f"Area Health ({self.area.name})"
        self._state = False

        self.distress_sensors = []

        # Check if there are binary sensors
        if BINARY_SENSOR_DOMAIN not in self.area.entities.keys():
            return

        # Fetch distress sensors
        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:

            if entity.device_class not in DISTRESS_SENSOR_CLASSES:
                continue

            self.distress_sensors.append(entity.entity_id)

        self._attributes = {
            "distress_sensors": self.distress_sensors,
            "active_sensors": [],
        }

        # Track presence sensors
        async_track_state_change(hass, self.distress_sensors, self.sensor_state_change)
        delta = timedelta(seconds=self.area.update_interval)

        # Timed self update
        async_track_time_interval(self.hass, self.update_area, delta)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return DEVICE_CLASS_PROBLEM

    def sensor_state_change(self, entity_id, from_state, to_state):
        self._update_state()

    def update_area(self, next_interval):
        self._update_state()

    def _update_state(self):

        self._state = self._get_health_state()
        self.schedule_update_ha_state()

    def _get_health_state(self):

        active_sensors = []

        # Loop over all entities and check their state
        for sensor in self.distress_sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.info(
                    f"Could not get sensor state: {sensor} entity not found, skipping"
                )
                continue

            if entity.state in DISTRESS_STATES:
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0


class AreaSensorGroupBinarySensor(BinarySensorEntity):
    def __init__(self, hass, area, device_class):
        """Initialize an area sensor group binary sensor."""

        self.area = area
        self.hass = hass
        self._device_class = device_class
        self._state = False

        device_class_name = device_class.capitalize()
        self._name = f"Area {device_class_name} ({self.area.name})"

        # Fetch sensors
        self.sensors = []
        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:

            if entity.device_class != self._device_class:
                continue

            self.sensors.append(entity.entity_id)

        self._attributes = {"sensors": self.sensors, "active_sensors": []}

        # Track presence sensors
        async_track_state_change(hass, self.sensors, self.sensor_state_change)
        delta = timedelta(seconds=self.area.update_interval)

        # Timed self update
        async_track_time_interval(self.hass, self.update_group, delta)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def sensor_state_change(self, entity_id, from_state, to_state):
        self._update_state()

    def update_group(self, next_interval):
        self._update_state()

    def _update_state(self):

        self._state = self._get_sensors_state()
        self.schedule_update_ha_state()

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

            if entity.state in STATE_ON:
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0


class GlobalSensorGroupBinarySensor(BinarySensorEntity):
    def __init__(self, hass, areas, device_class, location_name):
        """Initialize an area sensor group binary sensor."""

        self.hass = hass
        self._device_class = device_class
        self._state = False

        device_class_name = device_class.capitalize()
        location_title = location_name.capitalize()
        self._name = f"{location_title} {device_class_name}"

        self.update_interval = 0

        # Fetch sensors
        self.sensors = []
        for area in areas:
            for entity in area.entities[BINARY_SENSOR_DOMAIN]:

                if entity.device_class != self._device_class:
                    continue

                self.sensors.append(entity.entity_id)
                if area.update_interval > self.update_interval:
                    self.update_interval = area.update_interval

        self._attributes = {"sensors": self.sensors, "active_sensors": []}

        # Track presence sensors
        async_track_state_change(hass, self.sensors, self.sensor_state_change)
        delta = timedelta(seconds=self.update_interval)

        # Timed self update
        async_track_time_interval(self.hass, self.update_group, delta)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def sensor_state_change(self, entity_id, from_state, to_state):
        self._update_state()

    def update_group(self, next_interval):
        self._update_state()

    def _update_state(self):

        self._state = self._get_sensors_state()
        self.schedule_update_ha_state()

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

            if entity.state in STATE_ON:
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0
