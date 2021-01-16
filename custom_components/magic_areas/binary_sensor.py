DEPENDENCIES = ["magic_areas", "media_player", "binary_sensor"]

import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_OCCUPANCY,
    DEVICE_CLASS_PROBLEM,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    AGGREGATE_BINARY_SENSOR_CLASSES,
    AUTOLIGHTS_STATE_DISABLED,
    AUTOLIGHTS_STATE_NORMAL,
    AUTOLIGHTS_STATE_SLEEP,
    CONF_AL_DISABLE_ENTITY,
    CONF_AL_DISABLE_STATE,
    CONF_AL_ENTITIES,
    CONF_AL_SLEEP_ENTITY,
    CONF_AL_SLEEP_LIGHTS,
    CONF_AL_SLEEP_STATE,
    CONF_AL_SLEEP_TIMEOUT,
    CONF_AUTO_LIGHTS,
    CONF_CLEAR_TIMEOUT,
    CONF_CONTROL_CLIMATE,
    CONF_CONTROL_LIGHTS,
    CONF_CONTROL_MEDIA,
    CONF_EXTERIOR,
    CONF_ICON,
    CONF_ON_STATES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_UPDATE_INTERVAL,
    DISTRESS_SENSOR_CLASSES,
    DISTRESS_STATES,
    MODULE_DATA,
    PRESENCE_DEVICE_COMPONENTS,
)

_LOGGER = logging.getLogger(__name__)


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

            if sensor.device_class not in AGGREGATE_BINARY_SENSOR_CLASSES:
                continue

            available_device_classes.append(sensor.device_class)

        for device_class in set(available_device_classes):

            if device_class not in device_class_area_map.keys():
                device_class_area_map[device_class] = {"exterior": [], "interior": []}

            area_location = "exterior" if area.config.get(CONF_EXTERIOR) else "interior"
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


class AreaPresenceBinarySensor(BinarySensorEntity, RestoreEntity):
    def __init__(self, hass, area):
        """Initialize the area presence binary sensor."""

        self.area = area
        self.hass = hass
        self._name = f"Area ({self.area.name})"
        self._state = None
        self.last_off_time = datetime.utcnow()

        self.tracking_listeners = []

        _LOGGER.info(f"Area {self.area.slug} presence sensor initializing.")

        # Fetch presence sensors
        self.presence_sensors = []
        for component, entities in self.area.entities.items():

            if component not in PRESENCE_DEVICE_COMPONENTS:
                continue

            for entity in entities:

                if (
                    component == BINARY_SENSOR_DOMAIN
                    and entity.device_class
                    not in self.area.config.get(CONF_PRESENCE_SENSOR_DEVICE_CLASS)
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
            "clear_timeout": self.area.config.get(CONF_CLEAR_TIMEOUT),
            "update_interval": self.area.config.get(CONF_UPDATE_INTERVAL),
            "on_states": self.area.config.get(CONF_ON_STATES),
            "exterior": self.area.config.get(CONF_EXTERIOR),
            "automatic_lights": self._get_autolights_state(),
        }

        # Set attribute sleep_timeout if defined
        autolights_config = self.area.config.get(CONF_AUTO_LIGHTS)
        if autolights_config.get(CONF_AL_SLEEP_TIMEOUT):
            self._attributes["sleep_timeout"] = autolights_config.get(
                CONF_AL_SLEEP_TIMEOUT
            )

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
        if self.area.config.get(CONF_ICON):
            return self.area.config.get(CONF_ICON)
        return None

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return DEVICE_CLASS_OCCUPANCY

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._setup_listeners()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._setup_listeners
            )

        last_state = await self.async_get_last_state()
        is_new_entry = last_state is None  # newly added to HA

        if is_new_entry:
            _LOGGER.debug(f"New area detected: {self.area.slug}")
            self._update_state()
        else:
            _LOGGER.debug(f"Area restored: {self.area.slug} [{last_state.state}]")
            self._state = last_state.state == STATE_ON
            self.schedule_update_ha_state()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        self._remove_listeners()

    async def _setup_listeners(self, _=None) -> None:
        _LOGGER.debug("%s: Called '_setup_listeners'", self._name)
        if not self.hass.is_running:
            _LOGGER.debug("%s: Cancelled '_setup_listeners'", self._name)
            return

        # Track presence sensors
        remove_presence = async_track_state_change(
            self.hass, self.presence_sensors, self.sensor_state_change
        )

        autolights_config = self.area.config.get(CONF_AUTO_LIGHTS)

        # Track autolight_disable sensor if available
        if autolights_config.get(CONF_AL_DISABLE_ENTITY):
            remove_disable = async_track_state_change(
                self.hass,
                autolights_config.get(CONF_AL_DISABLE_ENTITY),
                self.autolight_disable_state_change,
            )
            self.tracking_listeners.append(remove_disable)

        # Track autolight_sleep sensor if available
        if autolights_config.get(CONF_AL_SLEEP_ENTITY):
            remove_sleep = async_track_state_change(
                self.hass,
                autolights_config.get(CONF_AL_SLEEP_ENTITY),
                self.autolight_sleep_state_change,
            )
            self.tracking_listeners.append(remove_sleep)

        # Timed self update
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))
        remove_interval = async_track_time_interval(self.hass, self.update_area, delta)

        self.tracking_listeners.extend([remove_presence, remove_interval])

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

    def autolight_sleep_state_change(self, entity_id, from_state, to_state):

        self._update_autolights_state()

    def autolight_disable_state_change(self, entity_id, from_state, to_state):

        last_state = self._attributes["automatic_lights"]
        self._update_autolights_state()

        # Check state change
        if self._attributes["automatic_lights"] != last_state:

            if to_state.state == self.area.config.get(CONF_AUTO_LIGHTS).get(
                CONF_AL_DISABLE_STATE
            ):
                if self._state:
                    self._lights_off()
            else:
                if self._state:
                    self._lights_on()

    def sensor_state_change(self, entity_id, from_state, to_state):

        _LOGGER.debug(
            f"Area {self.area.slug}: sensor '{entity_id}' changed to {to_state.state}"
        )

        if to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.utcnow()  # Update last_off_time

        return self._update_state()

    def update_area(self, next_interval):
        _LOGGER.debug(f"Area {self.area.slug}: Timed maintenance update")
        return self._update_state()

    def _update_autolights_state(self):

        self._attributes["automatic_lights"] = self._get_autolights_state()
        self.schedule_update_ha_state()

    def _get_autolights_state(self):

        if (
            not self.area.config.get(CONF_CONTROL_LIGHTS)
            or self._is_autolights_disabled()
        ):
            return AUTOLIGHTS_STATE_DISABLED

        if self._is_autolights_sleep():
            return AUTOLIGHTS_STATE_SLEEP

        return AUTOLIGHTS_STATE_NORMAL

    def _is_autolights_sleep(self):

        autolights_config = self.area.config.get(CONF_AUTO_LIGHTS)

        if autolights_config.get(CONF_AL_SLEEP_ENTITY):
            if not autolights_config.get(CONF_AL_SLEEP_LIGHTS):
                # If user fails to set CONF_AL_SLEEP_LIGHTS, sleep mode will be ignored
                _LOGGER.error(
                    f"'{CONF_AL_SLEEP_LIGHTS}' not defined. Please review your configuration."
                )
                return False

            sleep_entity = self.hass.states.get(
                autolights_config.get(CONF_AL_SLEEP_ENTITY)
            )
            if (
                sleep_entity.state.lower()
                == autolights_config.get(CONF_AL_SLEEP_STATE).lower()
            ):
                _LOGGER.info(
                    f"Sleep entity '{sleep_entity.entity_id}' on sleep state '{sleep_entity.state}'"
                )
                return True

        return False

    def _is_autolights_disabled(self):

        autolights_config = self.area.config.get(CONF_AUTO_LIGHTS)

        # Check if disabled
        if autolights_config.get(CONF_AL_DISABLE_ENTITY):
            disable_entity = self.hass.states.get(
                autolights_config.get(CONF_AL_DISABLE_ENTITY)
            )
            if disable_entity and (
                disable_entity.state.lower()
                == autolights_config.get(CONF_AL_DISABLE_STATE).lower()
            ):
                _LOGGER.info(
                    f"Disable entity '{disable_entity.entity_id}' on disable state '{disable_entity.state}'"
                )
                return True

        return False

    def _autolights(self):

        autolights_config = self.area.config.get(CONF_AUTO_LIGHTS)

        # All lights affected by default
        affected_lights = [
            entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]
        ]

        # Regular operation
        if autolights_config.get(CONF_AL_ENTITIES):
            affected_lights = autolights_config.get(CONF_AL_ENTITIES)

        # Check if in disable mode
        if self._is_autolights_disabled():
            return False

        # Check if in sleep mode
        if self._is_autolights_sleep():
            affected_lights = autolights_config.get(CONF_AL_SLEEP_LIGHTS)

        # Call service to turn_on the lights
        service_data = {ATTR_ENTITY_ID: affected_lights}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _update_state(self):

        area_state = self._get_area_state()
        last_state = self._state
        sleep_timeout = self.area.config.get(CONF_AUTO_LIGHTS).get(
            CONF_AL_SLEEP_TIMEOUT
        )

        if area_state:
            self._state = True
        else:
            if sleep_timeout and self._is_autolights_sleep():
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

        self.schedule_update_ha_state()

        # Check state change
        if last_state != self._state:

            if self._state:
                self._state_on()
            else:
                self._state_off()

    def _has_entities(self, domain):

        return domain in self.area.entities.keys()

    def _lights_on(self):
        # Turn on lights, if configured
        if self.area.config.get(CONF_CONTROL_LIGHTS) and self._has_entities(
            LIGHT_DOMAIN
        ):
            self._autolights()

    def _state_on(self):

        self._lights_on()

        # Turn on climate, if configured
        if self.area.config.get(CONF_CONTROL_CLIMATE) and self._has_entities(
            CLIMATE_DOMAIN
        ):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_ON, service_data)

    def _lights_off(self):
        # Turn off lights, if configured
        if self.area.config.get(CONF_CONTROL_LIGHTS) and self._has_entities(
            LIGHT_DOMAIN
        ):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[LIGHT_DOMAIN]
                ]
            }
            self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

    def _state_off(self):

        self._lights_off()

        # Turn off climate, if configured
        if self.area.config.get(CONF_CONTROL_CLIMATE) and self._has_entities(
            CLIMATE_DOMAIN
        ):
            service_data = {
                ATTR_ENTITY_ID: [
                    entity.entity_id for entity in self.area.entities[CLIMATE_DOMAIN]
                ]
            }
            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_TURN_OFF, service_data)

        # Turn off media, if configured
        if self.area.config.get(CONF_CONTROL_MEDIA) and self._has_entities(
            MEDIA_PLAYER_DOMAIN
        ):
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

            if entity.state in self.area.config.get(CONF_ON_STATES):
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
        self.tracking_listeners = []

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

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._setup_listeners()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._setup_listeners
            )

        self._update_state()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        self._remove_listeners()

    async def _setup_listeners(self, _=None) -> None:
        _LOGGER.debug("%s: Called '_setup_listeners'", self._name)
        if not self.hass.is_running:
            _LOGGER.debug("%s: Cancelled '_setup_listeners'", self._name)
            return

        # Track presence sensors
        remove_state_tracker = async_track_state_change(
            self.hass, self.distress_sensors, self.sensor_state_change
        )
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))

        # Timed self update
        remove_interval = async_track_time_interval(self.hass, self.update_area, delta)

        self.tracking_listeners.extend([remove_state_tracker, remove_interval])

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

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

        self.tracking_listeners = []

        # Fetch sensors
        self.sensors = []
        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:

            if entity.device_class != self._device_class:
                continue

            self.sensors.append(entity.entity_id)

        self._attributes = {"sensors": self.sensors, "active_sensors": []}

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

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._setup_listeners()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._setup_listeners
            )

        self._update_state()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        self._remove_listeners()

    async def _setup_listeners(self, _=None) -> None:
        _LOGGER.debug("%s: Called '_setup_listeners'", self._name)
        if not self.hass.is_running:
            _LOGGER.debug("%s: Cancelled '_setup_listeners'", self._name)
            return

        # Track presence sensors
        remove_state_tracker = async_track_state_change(
            self.hass, self.sensors, self.sensor_state_change
        )
        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))

        # Timed self update
        remove_interval = async_track_time_interval(self.hass, self.update_group, delta)

        self.tracking_listeners.extend([remove_state_tracker, remove_interval])

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

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

        self.tracking_listeners = []

        self.update_interval = 0

        # Fetch sensors
        self.sensors = []
        for area in areas:
            for entity in area.entities[BINARY_SENSOR_DOMAIN]:

                if entity.device_class != self._device_class:
                    continue

                self.sensors.append(entity.entity_id)
                if area.config.get(CONF_UPDATE_INTERVAL) > self.update_interval:
                    self.update_interval = area.config.get(CONF_UPDATE_INTERVAL)

        self._attributes = {"sensors": self.sensors, "active_sensors": []}

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

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._setup_listeners()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._setup_listeners
            )

        self._update_state()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        self._remove_listeners()

    async def _setup_listeners(self, _=None) -> None:
        _LOGGER.debug("%s: Called '_setup_listeners'", self._name)
        if not self.hass.is_running:
            _LOGGER.debug("%s: Cancelled '_setup_listeners'", self._name)
            return

        # Track presence sensors
        remove_state_tracker = async_track_state_change(
            self.hass, self.sensors, self.sensor_state_change
        )
        delta = timedelta(seconds=self.update_interval)

        # Timed self update
        remove_interval = async_track_time_interval(self.hass, self.update_group, delta)

        self.tracking_listeners.extend([remove_state_tracker, remove_interval])

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

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
