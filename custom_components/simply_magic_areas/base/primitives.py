from datetime import timedelta
from enum import StrEnum

from custom_components.simply_magic_areas.const import CONF_UPDATE_INTERVAL
from homeassistant.components.sensor import SensorStateClass
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from .entities import (
    MagicBinarySensorEntity,
    MagicEntity,
    MagicSensorEntity,
    MagicSwitchEntity,
)
from .magic import MagicArea


class MagicSensorBase(MagicEntity):
    """The base class for all the sensors int he magic area code."""

    sensors = []
    _device_class = None

    def __init__(self, area: MagicArea, device_class: StrEnum) -> None:
        """Initialize the magic sensor base with the area and device class."""
        MagicEntity.__init__(self, area)
        self.sensors = []
        self._device_class = device_class
        self._state = 0

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def _refresh_states(self, next_interval: int):
        self.logger.debug("Refreshing sensor states %s", self.name)
        return self._update_state()

    def update(self):
        """Update the state for this sensor."""
        self._update_state()

    def _update_state(self):
        self._state = self.get_sensors_state()
        self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        # Setup the listeners
        await self._setup_listeners()

        self._update_state()

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
            async_track_time_interval(self.hass, self._refresh_states, delta)
        )


class MagicAggregateBase(MagicSensorBase):
    """Aggregate base for the sensors."""

    def __init__(self, area: MagicArea, device_class: StrEnum) -> None:
        """Initialize the state for the aggregate sensor."""
        MagicSensorBase.__init__(self, area=area, device_class=device_class)
        self.attributes = {}

    def load_sensors(self, domain: str, unit_of_measurement: str | None = None):
        """Load the sensors for this element."""
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
            self.attributes = {
                "sensors": self.sensors,
                "unit_of_measurement": unit_of_measurement,
            }
        else:
            self.attributes = {"sensors": self.sensors, "active_sensors": []}


class SwitchBase(MagicSwitchEntity):
    """Base for the switches used in the magic area."""


class BinarySensorBase(MagicSensorBase, MagicBinarySensorEntity):
    """Base for the binary sensor used in the magic area."""


class BinarySensorGroupBase(MagicAggregateBase, MagicBinarySensorEntity):
    """Base for the binary sensor group used in the magic area."""


class SensorBase(MagicSensorBase, MagicSensorEntity):
    """Base for the sensors used in the magic area."""

    _state_class = SensorStateClass.MEASUREMENT


class SensorGroupBase(MagicAggregateBase, MagicSensorEntity):
    """Base for the sensor groups used in the magic area."""

    _state_class = SensorStateClass.MEASUREMENT
