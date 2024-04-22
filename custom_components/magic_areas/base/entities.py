"""Base classes for Magic Areas variants of Home Assistant entities."""

from datetime import datetime
import logging
from statistics import mean

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.group.light import LightGroup
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_OFF, STATE_ON
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from ..const import CONF_ON_STATES, DOMAIN, INVALID_STATES, MAGIC_DEVICE_ID_PREFIX

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity, Entity):
    """Basic Magic Areas Entity."""

    area = None
    _state = None
    _name = None
    logger = None
    _attributes = {}

    def __init__(self, area):
        """Initialize basic attributes and parent classes."""

        # Avoiding using super() due multiple inheritance issues
        Entity.__init__(self)
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(type(self).__module__)
        self._attributes = {}
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
            model="Magic Area",
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

    def update_state(self):
        """Refresh entity state."""
        return True

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
        """Refresh state when restoring state."""
        self.update_state()


class MagicBinarySensorEntity(MagicEntity, BinarySensorEntity):
    """Basic Magic Areas Binary Sensor Entity."""

    sensors = []
    last_off_time = None
    _state = False
    _mode = "single"

    def __init__(self, area, device_class):
        """Initialize parent classes."""
        MagicEntity.__init__(self, area)
        BinarySensorEntity.__init__(self, device_class)

        self.sensors = []

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id, from_state, to_state):
        """Handle change in state of tracked sensors."""

        if not to_state:
            return

        self.logger.debug(
            "%s: sensor '%s' changed to '%s'", self.name, entity_id, to_state.state
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state '%s'",
                self.name,
                entity_id,
                to_state.state,
            )
            return

        if to_state and to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.utcnow()  # Update last_off_time

        return self.update_state()

    def get_sensors_state(self, valid_states=None):
        """Fetch state from tracked sensors."""

        if valid_states is None:
            valid_states = [STATE_ON]

        self.logger.debug(
            "%s: Updating state. (Valid states: %s)", self.name, ",".join(valid_states)
        )

        active_sensors = []
        active_areas = set()

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        "%s: Could not get sensor state: '%s' entity not found, skipping",
                        self.name,
                        sensor,
                    )
                    continue

                self.logger.debug(
                    "%s: Sensor '%s' state: %s", self.name, sensor, entity.state
                )

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    self.logger.debug(
                        "%s: Sensor '%s' is unavailable, skipping...", self.name, sensor
                    )
                    continue

                if entity.state in valid_states:
                    self.logger.debug(
                        "%s: Valid presence sensor found: %s.", self.name, sensor
                    )
                    active_sensors.append(sensor)

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                self.logger.error(
                    "%s: Error getting entity state for '%s': %s",
                    self.name,
                    sensor,
                    str(e),
                )

        self._attributes["active_sensors"] = active_sensors

        # Make a copy that doesn't gets cleared out, for debugging
        if active_sensors:
            self._attributes["last_active_sensors"] = active_sensors

        self.logger.debug("%s: Active sensors: %s", self.name, str(active_sensors))

        if self.area.is_meta():
            active_areas = self.area.get_active_areas()
            self.logger.debug("[Area: {self.area.slug}] Active areas: {active_areas}")
            self._attributes["active_areas"] = active_areas

        if self._mode == "all":
            return len(active_sensors) == len(self.sensors)

        return len(active_sensors) > 0


class MagicSensorEntity(MagicEntity, SensorEntity):
    """Basic Magic Areas Sensor Entity."""

    _mode = "mean"
    sensors = []

    def sensor_state_change(self, entity_id, from_state, to_state):
        """Handle change in state of tracked sensors."""

        self.logger.debug(
            "%s: Sensor '%s' changed to '%s'", self.name, entity_id, to_state.state
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state '%s'",
                self.name,
                entity_id,
                to_state.state,
            )
            return None

        return self.update_state()

    def get_sensors_state(self):
        """Fetch state from tracked sensors."""

        sensor_values = []

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        "%s: Could not get sensor state: {sensor} entity not found, skipping",
                        self.name,
                    )
                    continue

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    continue

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                self.logger.error(
                    "%s: Error getting entity state for '%s': %s",
                    self.name,
                    sensor,
                    str(e),
                )
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                self.logger.info(
                    "%s: Non-numeric sensor value (%s) for entity '%s', skipping",
                    self.name,
                    str(e),
                    entity.entity_id,
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
    """Basic Magic Areas Sensor Entity."""

    _state = STATE_OFF

    def __init__(self, area):
        """Initialize parent class and state."""
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
            self.logger.debug(
                "%s: State restored [state=%s]", self.name, last_state.state
            )
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
    """Basic Magic Areas Light Group Entity."""

    def __init__(self, area, entities, name=None):
        """Initialize parent class and state."""
        MagicEntity.__init__(self, area)

        self._entities = entities

        self._name = name if name else f"{self.area.name} Lights"

        LightGroup.__init__(
            self, self.unique_id, self._name, self._entities, mode=False
        )
