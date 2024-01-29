from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.magic_areas.base import MagicEntity
from custom_components.magic_areas.base import MagicSensorBase
from custom_components.magic_areas.const import (
    CONF_ON_STATES,
    INVALID_STATES
)

class SwitchBase(MagicEntity, SwitchEntity):

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

class BinarySensorBase(MagicSensorBase, BinarySensorEntity):
    
    last_off_time = None
    _state = False

    def __init__(self, area, device_class):

        MagicSensorBase.__init__(self, area, device_class)
        BinarySensorEntity.__init__(self)

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id, from_state, to_state):
        self.logger.debug(f"{self.name}: sensor '{entity_id}' changed to {to_state.state}")

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                f"{self.name}: sensor '{entity_id}' has invalid state {to_state.state}"
            )
            return None

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

        self.logger.debug(f"[Area: {self.area.slug}] Active sensors: {active_sensors}")

        if self.area.is_meta():
            active_areas = self.area.get_active_areas()
            self.logger.debug("[Area: {self.area.slug}] Active areas: {active_areas}")
            self._attributes["active_areas"] = active_areas

        return len(active_sensors) > 0
    

class SensorBase(MagicSensorBase, SensorEntity):
    _mode = "mean"

    @property
    def state(self):
        """Return the state of the entity"""
        return self._state

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