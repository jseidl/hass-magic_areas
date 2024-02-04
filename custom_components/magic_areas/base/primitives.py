from datetime import timedelta

from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.components.sensor.const import SensorStateClass

from custom_components.magic_areas.base.entities import (
    MagicEntity,
    MagicSwitchEntity,
    MagicSensorEntity,
    MagicBinarySensorEntity
)
from custom_components.magic_areas.const import (
    CONF_UPDATE_INTERVAL
)

class MagicSensorBase(MagicEntity):

    sensors = []
    _device_class = None

    def __init__(self, area, device_class):

        MagicEntity.__init__(self, area)
        self.sensors = list()
        self._device_class = device_class

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def refresh_states(self, next_interval):
        self.logger.debug(f"Refreshing sensor states {self.name}")
        return self.update_state()
    
    def update(self):
        self.update_state()

    def update_state(self):
        self._state = self.get_sensors_state()
        self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        # Setup the listeners
        await self._setup_listeners()

        self.update_state()

    async def _setup_listeners(self, _=None) -> None:
        self.logger.debug("%s: Called '_setup_listeners'", self._name)
        if not self.hass.is_running:
            self.logger.debug("%s: Cancelled '_setup_listeners'", self._name)
            return

        # Track presence sensors
        self.async_on_remove(
            async_track_state_change(self.hass, self.sensors, self.sensor_state_change)
        )

        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))

        # Timed self update
        self.async_on_remove(
            async_track_time_interval(self.hass, self.refresh_states, delta)
        )

class MagicAggregateBase(MagicSensorBase):
    def load_sensors(self, domain, unit_of_measurement=None):
        # Fetch sensors
        self.sensors = []
        for entity in self.area.entities[domain]:
            if "device_class" not in entity.keys():
                continue

            if entity["device_class"] != self._device_class:
                continue

            if unit_of_measurement:
                if "unit_of_measurement" not in entity.keys():
                    continue
                if entity["unit_of_measurement"] != unit_of_measurement:
                    continue

            self.sensors.append(entity["entity_id"])

        if unit_of_measurement:
            self._attributes = {
                "sensors": self.sensors,
                "unit_of_measurement": unit_of_measurement,
            }
        else:
            self._attributes = {"sensors": self.sensors, "active_sensors": []}

class SwitchBase(MagicSwitchEntity):
    pass
    
class BinarySensorBase(MagicSensorBase, MagicBinarySensorEntity):
    pass

class BinarySensorGroupBase(MagicAggregateBase, MagicBinarySensorEntity):
    pass

class SensorBase(MagicSensorBase, MagicSensorEntity):
    _state_class = SensorStateClass.MEASUREMENT

class SensorGroupBase(MagicAggregateBase, MagicSensorEntity):
    _state_class = SensorStateClass.MEASUREMENT