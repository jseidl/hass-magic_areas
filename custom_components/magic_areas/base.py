import logging
import voluptuous as vol

from statistics import mean
from copy import deepcopy
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity import Entity

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.setup import async_setup_component
from homeassistant.util import slugify
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    STATE_UNAVAILABLE,
    STATE_ON
)

from .const import (
    CONF_ON_STATES,
    CONF_INCLUDE_ENTITIES,
    CONF_EXCLUDE_ENTITIES,
    CONF_ENABLED_FEATURES,
    CONF_UPDATE_INTERVAL,
    DEVICE_CLASS_DOMAINS,
    _DOMAIN_SCHEMA,
    DOMAIN,
    EVENT_MAGICAREAS_AREA_READY,
)


CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: _DOMAIN_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)

class MagicSensorBase:

    name = None
    hass = None
    _attributes = {}
    area = None

    sensors = []

    tracking_listeners = []

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name


    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    def refresh_states(self, next_interval):
        _LOGGER.debug(f"Refreshing sensor states {self.name}")
        return self._update_state()

    def _update_state(self):
        
        self._state = self._get_sensors_state()
        self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        # Setup the listeners
        await self._setup_listeners()

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

    async def _shutdown(self) -> None:
        await self._remove_listeners()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        await self._shutdown()

class SensorBase(MagicSensorBase, RestoreEntity, Entity):

    _mode = 'mean'

    @property
    def state(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id, from_state, to_state):
        
        _LOGGER.debug(
            f"{self.name}: sensor '{entity_id}' changed to {to_state.state}"
        )

        return self._update_state()

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

            # Skip unavailable entities
            if entity.state == STATE_UNAVAILABLE:
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                err_str = str(e)
                _LOGGER.info(
                    f"Non-numeric sensor value ({err_str}) for entity {entity.entity_id}, skipping"
                )
                continue

        ret = 0.0

        if sensor_values:
            if self._mode == 'sum':
                ret = sum(sensor_values)
            else:
                ret = mean(sensor_values)
        
        return round(ret, 2)

class BinarySensorBase(MagicSensorBase, BinarySensorEntity, RestoreEntity):

    _device_class = None

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id, from_state, to_state):
        
        _LOGGER.debug(
            f"{self.name}: sensor '{entity_id}' changed to {to_state.state}"
        )

        if to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.utcnow()  # Update last_off_time

        return self._update_state()

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

            if entity.state in STATE_ON:
                active_sensors.append(sensor)

        self._attributes["active_sensors"] = active_sensors

        return len(active_sensors) > 0

class AggregateBase(MagicSensorBase):

    def load_sensors(self, domain, unit_of_measurement=None):

        # Fetch sensors
        self.sensors = []
        for entity in self.area.entities[domain]:

            if 'device_class' not in entity.keys():
                continue

            if entity['device_class'] != self._device_class:
                continue

            if unit_of_measurement:
                if 'unit_of_measurement' not in entity.keys():
                    continue
                if entity['unit_of_measurement'] != unit_of_measurement:
                    continue

            self.sensors.append(entity['entity_id'])

        if unit_of_measurement:
            self._attributes = {"sensors": self.sensors, "unit_of_measurement": unit_of_measurement}
        else:
            self._attributes = {"sensors": self.sensors, "active_sensors": []}

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._initialize()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._initialize
            )

        self._update_state()

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
        remove_interval = async_track_time_interval(self.hass, self.refresh_states, delta)

        self.tracking_listeners.extend([remove_state_tracker, remove_interval])

class MagicArea(object):

    def __init__(self, hass, area, config) -> None:

        self.hass = hass
        self.name = area.name
        self.id = area.id
        self.slug = slugify(self.name)
        self.hass_config = config
        self.initialized = False

        self.entities = {}

        # Check if area is defined on YAML, if not, generate default config
        if self.slug not in self.hass_config.keys():
            default_config = {f"{self.slug}": {}}
            self.config = _DOMAIN_SCHEMA(default_config)[self.slug]
        else:
            self.config = self.hass_config[self.slug]

        # Add callback for initialization
        self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self.initialize
            )

    def has_feature(self, feature) -> bool:

        return feature in self.config.get(CONF_ENABLED_FEATURES)

    def _is_valid_entity(self, entity_object) -> bool:

        if entity_object.disabled:
            return False
        
        if entity_object.entity_id in self.config.get(CONF_EXCLUDE_ENTITIES):
            return False

        return True

    async def _is_entity_from_area(self, entity_object) -> bool:

        # Check entity's area_id
        if entity_object.area_id == self.id:
            return True

        # Check device's area id, if available
        if entity_object.device_id:

            device_registry = await self.hass.helpers.device_registry.async_get_registry()
            if entity_object.device_id in device_registry.devices.keys():
                device_object = device_registry.devices[entity_object.device_id]
                if device_object.area_id == self.id:
                    return True

        # Check if entity_id is in CONF_INCLUDE_ENTITIES
        if entity_object.entity_id in self.config.get(CONF_INCLUDE_ENTITIES):
            return True

        return False

    async def load_entities(self) -> None:

        entity_list = []
        include_entities = self.config.get(CONF_INCLUDE_ENTITIES)

        entity_registry = await self.hass.helpers.entity_registry.async_get_registry()

        for entity_id, entity_object in entity_registry.entities.items():

            # Check entity validity
            if not self._is_valid_entity(entity_object):
                continue

            # Check area membership
            area_membership = await self._is_entity_from_area(entity_object)

            if not area_membership:
                continue

            entity_list.append(entity_id)

        if include_entities:
            entity_list.extend(include_entities)

        for entity_id in entity_list:

            entity_component, entity_name = entity_id.split('.')

            # Get latest state and create object
            latest_state = self.hass.states.get(entity_id)
            updated_entity = {
                'entity_id': entity_id
            }
            
            if latest_state:
                updated_entity.update(latest_state.attributes)

            if entity_component not in self.entities.keys():
                self.entities[entity_component] = []

            self.entities[entity_component].append(updated_entity)
            
        _LOGGER.debug(f"Loaded entities for area {self.slug}: {self.entities}")

    async def initialize(self, _=None) -> None:
        _LOGGER.debug(f"Initializing area {self.slug}...")
        
        await self.load_entities()

        self.initialized = True

        self.hass.bus.async_fire(EVENT_MAGICAREAS_AREA_READY)

        _LOGGER.debug(f"Area {self.slug} initialized.")
