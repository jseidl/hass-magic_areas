DEPENDENCIES = ['magic_areas']

import logging

from datetime import timedelta, datetime
from time import sleep

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_DOOR,
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE, 
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_GAS,
    BinarySensorEntity
)

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from homeassistant.helpers.event import async_track_state_change, async_track_time_interval 
from homeassistant.const import STATE_ON, STATE_OFF, STATE_HOME, STATE_PROBLEM, STATE_ALARM_TRIGGERED, ATTR_ENTITY_ID, SERVICE_TURN_ON, SERVICE_TURN_OFF

from . import MODULE_DATA

_LOGGER = logging.getLogger(__name__)

SLEEP_TIME = .3 # seconds

PRESENCE_DEVICE_COMPONENTS = [MEDIA_PLAYER_DOMAIN, BINARY_SENSOR_DOMAIN] #@todo make configurable
DISTRESS_SENSOR_CLASSES = [
    DEVICE_CLASS_PROBLEM,
    DEVICE_CLASS_SMOKE, 
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SAFETY,
    DEVICE_CLASS_GAS,
] # @todo make configurable
DISTRESS_STATES = [
    STATE_ALARM_TRIGGERED,
    STATE_ON,
    STATE_PROBLEM
]

async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument
    
    areas = hass.data.get(MODULE_DATA)

    entities = []

    async_add_entities([AreaPresenceBinarySensor(hass, area) for area in areas])
    async_add_entities([AreaDistressBinarySensor(hass, area) for area in areas])

    # Create Aggregate Sensors
    aggregate_sensors = []
    for area in areas:
        available_device_classes = []

        # Skip areas without binary_sensor
        if BINARY_SENSOR_DOMAIN not in area.entities.keys():
            continue

        for sensor in area.entities[BINARY_SENSOR_DOMAIN]:
            if sensor.device_class not in [DEVICE_CLASS_DOOR, DEVICE_CLASS_MOTION]:
                continue
            available_device_classes.append(sensor.device_class)

        for device_class in set(available_device_classes):
            aggregate_sensors.append(AreaSensorGroupBinarySensor(hass, area, device_class))

    async_add_entities(aggregate_sensors)

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

        _LOGGER.warn(f"Area {self.area.slug} presence sensor initializing.")

        # Fetch presence sensors
        self.presence_sensors = []
        for component, entities in self.area.entities.items():

            if component not in PRESENCE_DEVICE_COMPONENTS:
                continue

            for entity in entities:

                if (component == BINARY_SENSOR_DOMAIN and entity.device_class not in self.area.presence_device_class):
                    continue

                self.presence_sensors.append(entity.entity_id)

        # Append presence_hold switch as a presence_sensor
        presence_hold_switch_id = f"{SWITCH_DOMAIN}.area_presence_hold_{self.area.slug}"
        self.presence_sensors.append(presence_hold_switch_id)
        
        # Set attributes
        self._attributes = {
            'presence_sensors': self.presence_sensors,
            'active_sensors':   [],
            'clear_timeout':    self.area.clear_timeout,
            'update_interval':  self.area.update_interval,
            'on_states':        self.area.on_states,
        }

        # Track presence sensors
        async_track_state_change(hass, self.presence_sensors, self.sensor_state_change)
        delta = timedelta(seconds=self.area.update_interval)

        # Timed self update
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

    def sensor_state_change(self, entity_id, from_state, to_state):
        if to_state.state == STATE_OFF:
                self.last_off_time = datetime.utcnow() # Update last_off_time

        return self._update_state()

    def update_area(self, next_interval):
        return self._update_state()

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
            if self._state:
                self._state_on()
            else:
                self._state_off()

    def _has_entities(self, domain):

        return domain in self.area.entities.keys()

    def _state_on(self):

        # Turn on lights, if configured
        if self.area.control_lights and self._has_entities(LIGHT_DOMAIN):
            if not self.area.automatic_lights:
                service_data = {ATTR_ENTITY_ID: [entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]]}
                self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)
            else:
                service_data = {ATTR_ENTITY_ID: self.area.automatic_lights}
                self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        # Turn on climate, if configured
        if self.area.control_climate and self._has_entities(CLIMATE_DOMAIN):
            service_data = {ATTR_ENTITY_ID: [entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]]}
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_ON, service_data)

    def _state_off(self):

        # Turn off lights, if configured
        if self.area.control_lights and self._has_entities(LIGHT_DOMAIN):
            service_data = {ATTR_ENTITY_ID: [entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]]}
            self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)
        
        # Turn off climate, if configured
        if self.area.control_climate and self._has_entities(CLIMATE_DOMAIN):
            service_data = {ATTR_ENTITY_ID: [entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]]}
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_OFF, service_data)

        # Turn off media, if configured
        if self.area.control_media and self._has_entities(MEDIA_PLAYER_DOMAIN):
            service_data = {ATTR_ENTITY_ID: [entity.entity_id for entity in self.area.entities[MEDIA_PLAYER_DOMAIN]]}
            self.hass.services.call(MEDIA_PLAYER_DOMAIN, SERVICE_TURN_OFF, service_data)

    def _get_area_state(self):

        active_sensors = []

        # Loop over all entities and check their state
        for sensor in self.presence_sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.warn(f"{sensor} entity not found")
                continue

            if entity.state in self.area.on_states:
                active_sensors.append(sensor)

        self._attributes['active_sensors'] = active_sensors

        return (len(active_sensors) > 0)

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

            if (entity.device_class not in DISTRESS_SENSOR_CLASSES):
                continue

            self.distress_sensors.append(entity.entity_id)

        self._attributes = {
            'distress_sensors': self.distress_sensors,
            'active_sensors': []
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
                _LOGGER.warn(f"{sensor} entity not found")
                continue

            if entity.state in DISTRESS_STATES:
                active_sensors.append(sensor)

        self._attributes['active_sensors'] = active_sensors

        return (len(active_sensors) > 0)

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

            if (entity.device_class != self._device_class):
                continue

            self.sensors.append(entity.entity_id)

        self._attributes = {
            'sensors': self.sensors,
            'active_sensors': []
        }

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
                _LOGGER.warn(f"{sensor} entity not found")
                continue

            if entity.state in STATE_ON:
                active_sensors.append(sensor)

        self._attributes['active_sensors'] = active_sensors

        return (len(active_sensors) > 0)