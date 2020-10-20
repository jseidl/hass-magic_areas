DEPENDENCIES = ["magic_areas"]

import logging
from datetime import datetime, timedelta
from statistics import mean
from time import sleep

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    STATE_ON,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from . import MODULE_DATA

_LOGGER = logging.getLogger(__name__)

SLEEP_TIME = 0.3  # seconds

AGGREGATE_SENSOR_CLASSES = (
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_ILLUMINANCE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
)


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument

    areas = hass.data.get(MODULE_DATA)

    entities = []

    # Create Aggregate Sensors
    aggregate_sensors = []
    device_class_area_map = {}
    for area in areas:
        available_device_classes = []

        # sensor Aggregates
        if SENSOR_DOMAIN not in area.entities.keys():
            continue

        for sensor in area.entities[SENSOR_DOMAIN]:
            if sensor.device_class not in AGGREGATE_SENSOR_CLASSES:
                continue
            available_device_classes.append(sensor.device_class)

        for device_class in set(available_device_classes):

            if device_class not in device_class_area_map.keys():
                device_class_area_map[device_class] = {"exterior": [], "interior": []}

            area_location = "exterior" if area.exterior else "interior"
            device_class_area_map[device_class][area_location].append(area)

            _LOGGER.info(f"Creating aggregate sensor for {area.name}/{device_class}")
            aggregate_sensors.append(AreaSensorGroupSensor(hass, area, device_class))

    if aggregate_sensors:
        async_add_entities(aggregate_sensors)

    # Add Global Aggregates
    global_aggregates = []
    for device_class, locations in device_class_area_map.items():
        for location_name, areas in locations.items():
            if areas:
                global_aggregates.append(
                    GlobalSensorGroupSensor(hass, areas, device_class, location_name)
                )

    if global_aggregates:
        async_add_entities(global_aggregates)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class AreaSensorGroupSensor(Entity):
    def __init__(self, hass, area, device_class):
        """Initialize an area sensor group sensor."""

        self.area = area
        self.hass = hass
        self._device_class = device_class
        self._state = 0

        device_class_name = device_class.capitalize()
        self._name = f"Area {device_class_name} ({self.area.name})"

        # Fetch sensors
        self.sensors = []
        uom_candidates = []  # candidates for unit_of_measurement
        for entity in self.area.entities[SENSOR_DOMAIN]:

            if entity.device_class != self._device_class:
                continue

            self.sensors.append(entity.entity_id)
            uom_candidates.append(entity.unit_of_measurement)

        # Elect unit_of_measurement
        self._unit_of_measurement = max(set(uom_candidates), key=uom_candidates.count)

        self._attributes = {"sensors": self.sensors}

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
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def state(self):
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

        sensor_values = []

        # Loop over all entities and check their state
        for sensor in self.sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.info(
                    f"Could not get sensor state: {sensor} entity not found, skipping"
                )
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                err_str = str(e)
                _LOGGER.info(
                    f"Non-numeric sensor value ({err_str}) for entity {entity.entity_id}, skipping"
                )
                continue

        if sensor_values:
            return round(mean(sensor_values), 2)
        else:
            return 0


class GlobalSensorGroupSensor(Entity):
    def __init__(self, hass, areas, device_class, location_name):

        self.hass = hass
        self._device_class = device_class
        self._state = False

        device_class_name = device_class.capitalize()
        location_title = location_name.capitalize()
        self._name = f"{location_title} {device_class_name}"

        self.update_interval = 0

        # Fetch sensors
        self.sensors = []
        uom_candidates = []
        for area in areas:
            for entity in area.entities[SENSOR_DOMAIN]:

                if entity.device_class != self._device_class:
                    continue

                self.sensors.append(entity.entity_id)
                uom_candidates.append(entity.unit_of_measurement)

                if area.update_interval > self.update_interval:
                    self.update_interval = area.update_interval

        # Elect unit_of_measurement
        self._unit_of_measurement = max(set(uom_candidates), key=uom_candidates.count)

        self._attributes = {"sensors": self.sensors}

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
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def state(self):
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

        sensor_values = []

        # Loop over all entities and check their state
        for sensor in self.sensors:

            entity = self.hass.states.get(sensor)

            if not entity:
                _LOGGER.info(
                    f"Could not get sensor state: {sensor} entity not found, skipping"
                )
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                err_str = str(e)
                _LOGGER.info(
                    f"Non-numeric sensor value ({err_str}) for entity {entity.entity_id}, skipping"
                )
                continue

        if sensor_values:
            return round(mean(sensor_values), 2)
        else:
            return 0
