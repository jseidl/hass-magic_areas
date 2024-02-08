import logging

from statistics import mean
from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.group.light import LightGroup
from homeassistant.const import STATE_ON, STATE_OFF

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.device_registry import DeviceInfo

from custom_components.magic_areas.const import (
    CONF_ON_STATES,
    INVALID_STATES,
    DOMAIN,
    MAGIC_DEVICE_ID_PREFIX,
)

_LOGGER = logging.getLogger(__name__)

class MagicEntity(RestoreEntity, Entity):

    area = None
    _state = None
    _name = None
    logger = None
    _attributes = {}

    def __init__(self, area):

        # Avoiding using super() due multiple inheritance issues
        Entity.__init__(self)
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(type(self).__module__)
        self._attributes = dict()
        self.area = area

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.area.id}")
            },
            name=self.area.name,
            manufacturer="Magic Areas",
            model="Magic Area"
        )

    @property
    def unique_id(self):
        """Return a unique ID."""
        name_slug = slugify(self._name)
        return f"{name_slug}"

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the attributes of the entity."""
        return self._attributes

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._initialize()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._initialize
            )

        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""

        await self._shutdown()
        await super().async_will_remove_from_hass()

    async def restore_state(self):
        self.update_state()

class MagicBinarySensorEntity(MagicEntity, BinarySensorEntity):
    
    last_off_time = None
    _state = False
    _mode = "single"

    def __init__(self, area, device_class):

        MagicEntity.__init__(self, area)
        BinarySensorEntity.__init__(self, device_class)

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id, from_state, to_state):

        if not to_state:
            return

        self.logger.debug(f"{self.name}: sensor '{entity_id}' changed to {to_state.state}")

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                f"{self.name}: sensor '{entity_id}' has invalid state {to_state.state}"
            )
            return

        if to_state and to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.utcnow()  # Update last_off_time

        return self.update_state()

    def get_sensors_state(self, valid_states=[STATE_ON]):
        self.logger.debug(
            f"[Area: {self.area.slug}] Updating state. (Valid states: {valid_states})"
        )

        active_sensors = []
        active_areas = set()

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        f"[Area: {self.area.slug}] Could not get sensor state: {sensor} entity not found, skipping"
                    )
                    continue

                self.logger.debug(
                    f"[Area: {self.area.slug}] Sensor {sensor} state: {entity.state}"
                )

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    self.logger.debug(
                        f"[Area: {self.area.slug}] Sensor '{sensor}' is unavailable, skipping..."
                    )
                    continue

                if entity.state in valid_states:
                    self.logger.debug(
                        f"[Area: {self.area.slug}] Valid presence sensor found: {sensor}."
                    )
                    active_sensors.append(sensor)

            except Exception as e:
                self.logger.error(
                    f"[{self.name}] Error getting entity state for '{sensor}': {str(e)}"
                )
                pass

        self._attributes["active_sensors"] = active_sensors

        # Make a copy that doesn't gets cleared out, for debugging
        if active_sensors:
            self._attributes["last_active_sensors"] = active_sensors

        self.logger.debug(f"[Area: {self.area.slug}] Active sensors: {active_sensors}")

        if self.area.is_meta():
            active_areas = self.area.get_active_areas()
            self.logger.debug("[Area: {self.area.slug}] Active areas: {active_areas}")
            self._attributes["active_areas"] = active_areas

        if self._mode == 'all':
            return (len(active_sensors) == len(self.sensors))
        else:
            return len(active_sensors) > 0

class MagicSensorEntity(MagicEntity, SensorEntity):
    _mode = "mean"

    @property
    def state(self):
        """Return the state of the entity"""
        return self.get_sensors_state()

    def sensor_state_change(self, entity_id, from_state, to_state):
        self.logger.debug(f"{self.name}: sensor '{entity_id}' changed to {to_state.state}")

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                f"{self.name}: sensor '{entity_id}' has invalid state {to_state.state}"
            )
            return None

        return self.update_state()

    def get_sensors_state(self):
        sensor_values = []

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        f"[{self.name}] Could not get sensor state: {sensor} entity not found, skipping"
                    )
                    continue

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    continue

            except Exception as e:
                self.logger.error(
                    f"[{self.name}] Error getting entity state for '{sensor}': {str(e)}"
                )
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                err_str = str(e)
                self.logger.info(
                    f"[{self.name}] Non-numeric sensor value ({err_str}) for entity {entity.entity_id}, skipping"
                )
                continue

        ret = 0.0

        if sensor_values:
            if self._mode == "sum":
                ret = sum(sensor_values)
            else:
                ret = mean(sensor_values)

        return round(ret, 2)
    

class MagicSwitchEntity(MagicEntity, SwitchEntity):

    _state = STATE_OFF

    def __init__(self, area):

        super().__init__(area)
        self._state = STATE_OFF

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state == STATE_ON

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""

        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(f"Switch {self.name} restored [state={last_state.state}]")
            self._state = last_state.state
        else:
            self._state = STATE_OFF

        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._state = STATE_OFF
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = STATE_ON
        self.schedule_update_ha_state()

class MagicLightGroup(MagicEntity, LightGroup):
    
    def __init__(self, area, entities, init_group=True):

        MagicEntity.__init__(self, area)

        self._entities = entities

        self._name = f"{self.area.name} Lights"

        if init_group:
            self.init_group()

    def init_group(self):
        LightGroup.__init__(
            self, self.unique_id, self._name, self._entities, mode=False
        )