"""Base classes for Home Assistant primitive entities."""

from datetime import timedelta

from homeassistant.components.sensor.const import SensorStateClass
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from ..base.entities import (
    MagicBinarySensorEntity,
    MagicEntity,
    MagicSensorEntity,
    MagicSwitchEntity,
)
from ..const import CONF_UPDATE_INTERVAL


class MagicSensorBase(MagicEntity):
    """Base class common to both Binary Sensor and Sensor entities."""

    sensors = []
    _device_class = None

    def __init__(self, area, device_class):
        """Initialize parent class and variables."""
        MagicEntity.__init__(self, area)
        self.sensors = []
        self._device_class = device_class

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def refresh_states(self, next_interval):
        """Refresh sensor state from tracked sensors."""
        self.logger.debug("%s: Refreshing sensor states.", self.name)
        return self.update_state()

    def update(self):
        """Update sensor state."""
        self.update_state()

    def get_sensors_state(self, valid_states=None):
        """Return tracked sensors' state."""
        return []

    def sensor_state_change(self, from_state, to_state):
        """Handle change in tracked sensors' state."""
        return False

    def update_state(self):
        """Update sensor state."""
        self._state = self.get_sensors_state()
        self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        """Set up listeners and update state."""
        # Setup the listeners
        await self._setup_listeners()

        self.update_state()

    async def _setup_listeners(self, _=None) -> None:
        """Set up event listeners."""
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
    """Base class for Aggregate sensors."""

    def load_sensors(self, domain, unit_of_measurement=None):
        """Load entities into entity list."""
        # Fetch sensors
        self.sensors = []
        for entity in self.area.entities[domain]:
            if "device_class" not in entity:
                continue

            if entity["device_class"] != self._device_class:
                continue

            if unit_of_measurement:
                if "unit_of_measurement" not in entity:
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
    """Base class for Switch entities."""


class BinarySensorBase(MagicSensorBase, MagicBinarySensorEntity):
    """Base class for Binary Sensor entities."""


class BinarySensorGroupBase(MagicAggregateBase, MagicBinarySensorEntity):
    """Base class for Group Binary Sensor entities."""


class SensorBase(MagicSensorBase, MagicSensorEntity):
    """Base class for Sensor entities."""

    _state_class = SensorStateClass.MEASUREMENT


class SensorGroupBase(MagicAggregateBase, MagicSensorEntity):
    """Base class for Group Sensor entities."""

    _state_class = SensorStateClass.MEASUREMENT
