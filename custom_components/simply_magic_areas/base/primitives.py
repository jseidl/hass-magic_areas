from datetime import timedelta, datetime
from enum import StrEnum
from typing import Any

from custom_components.simply_magic_areas.const import CONF_UPDATE_INTERVAL
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.core import Event, EventStateChangedData
from homeassistant.const import STATE_OFF
from homeassistant.helpers.event import (
    async_track_state_change_event,
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

    sensors: list[str] = []
    _device_class: SensorDeviceClass | None = None

    def __init__(self, area: MagicArea, device_class: SensorDeviceClass) -> None:
        """Initialize the magic sensor base with the area and device class."""
        MagicEntity.__init__(self, area)
        self.sensors = []
        self._device_class = device_class
        self._state = 0

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the class of this binary_sensor."""
        return self._device_class

    def _refresh_states(self, next_interval: int) -> None:
        self.logger.debug("Refreshing sensor states %s", self.name)
        return self._update_state()

    def update(self) -> None:
        """Update the state for this sensor."""
        self._update_state()

    def _update_state(self) -> None:
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
            async_track_state_change_event(
                self.hass, self.sensors, self.sensor_state_change
            )
        )

        delta = timedelta(seconds=self.area.config.get(CONF_UPDATE_INTERVAL))

        # Timed self update
        self.async_on_remove(
            async_track_time_interval(self.hass, self._refresh_states, delta)
        )

    def sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Deal with the sensor state changing."""


class MagicBinarySensorBase(MagicEntity):
    """The base class for all the sensors int he magic area code."""

    sensors: list[str] = []
    _device_class: BinarySensorDeviceClass | None = None

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Initialize the magic sensor base with the area and device class."""
        MagicEntity.__init__(self, area)
        self.sensors = []
        self._device_class = device_class
        self._state = STATE_OFF

    @property
    def device_class(self) -> BinarySensorDeviceClass:
        """Return the class of this binary_sensor."""
        return self._device_class

    def _refresh_states(self, next_interval: datetime) -> None:
        self.logger.debug("Refreshing sensor states %s", self.name)
        return self._update_state()

    def update(self) -> None:
        """Update the state for this sensor."""
        self._update_state()

    def _update_state(self) -> None:
        self._state = self.get_sensors_state()
        self.schedule_update_ha_state()

    def get_sensors_state(self, valid_states: list | None = None) -> int:
        """Return the current sensor state."""
        yield

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
            async_track_state_change_event(
                self.hass, self.sensors, self.sensor_state_change
            )
        )

        delta = timedelta(
            seconds=float(self.area.config.get(CONF_UPDATE_INTERVAL, 0.0))
        )

        # Timed self update
        self.async_on_remove(
            async_track_time_interval(self.hass, self._refresh_states, delta)
        )

    def sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Deal with the sensor state changing."""


class MagicAggregateBase(MagicSensorBase):
    """Aggregate base for the sensors."""

    def __init__(self, area: MagicArea, device_class: SensorDeviceClass) -> None:
        """Initialize the state for the aggregate sensor."""
        MagicSensorBase.__init__(self, area=area, device_class=device_class)
        self.attributes: dict[str, Any] = {}

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


class MagicBinaryAggregateBase(MagicBinarySensorBase):
    """Aggregate base for the sensors."""

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Initialize the state for the aggregate sensor."""
        MagicBinarySensorBase.__init__(self, area=area, device_class=device_class)
        self.attributes: dict[str, Any] = {}

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


class BinarySensorBase(MagicBinarySensorEntity):
    """Base for the binary sensor used in the magic area."""


class BinarySensorGroupBase(MagicBinaryAggregateBase, MagicBinarySensorEntity):
    """Base for the binary sensor group used in the magic area."""

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Run the setup of the class calling the inhereted inits."""
        MagicBinaryAggregateBase.__init__(self, area=area, device_class=device_class)
        MagicBinarySensorEntity.__init__(self, area=area, device_class=device_class)


class SensorBase(MagicSensorBase, MagicSensorEntity):
    """Base for the sensors used in the magic area."""

    _state_class = SensorStateClass.MEASUREMENT

    def __init__(self, area: MagicArea, device_class: SensorDeviceClass) -> None:
        """Run the setup of the class calling the inhereted inits."""
        MagicSensorBase.__init__(self, area=area, device_class=device_class)
        MagicSensorEntity.__init__(self, area=area)


class SensorGroupBase(MagicAggregateBase, MagicSensorEntity):
    """Base for the sensor groups used in the magic area."""

    _state_class = SensorStateClass.MEASUREMENT

    def __init__(self, area: MagicArea, device_class: SensorDeviceClass) -> None:
        """Run the setup of the class calling the inhereted inits."""
        MagicAggregateBase.__init__(self, area=area, device_class=device_class)
        MagicSensorEntity.__init__(self, area=area)
