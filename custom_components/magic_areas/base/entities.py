"""The basic entities for magic areas."""

from datetime import datetime
import logging
from statistics import mean

from .magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_ON_STATES,
    DOMAIN,
    INVALID_STATES,
    MAGIC_DEVICE_ID_PREFIX,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.group.light import LightGroup
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_OFF, STATE_ON
from homeassistant.core import State
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)


class MagicEntity(RestoreEntity, Entity):
    """MagicEntity is the base entity for use with all the magic classes."""

    area: MagicArea = None
    _state: str = None
    _name: str = None
    logger: logging.Logger = None
    _attributes: dict = {}

    def __init__(self, area: MagicArea) -> None:
        """Initialize the magic area."""
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
    def unique_id(self) -> str:
        """Return a unique ID."""
        name_slug = slugify(self._name)
        return f"{name_slug}"

    @property
    def name(self) -> str:
        """Return the name of the device if any."""
        return self._name

    @property
    def should_poll(self) -> str:
        """If entity should be polled."""
        return False

    @property
    def extra_state_attributes(self) -> str:
        """Return the attributes of the entity."""
        return self._attributes

    async def _initialize(self) -> None:
        pass

    async def _shutdown(self) -> None:
        pass

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._initialize()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._initialize
            )

        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Remove the listeners upon removing the component."""

        await self._shutdown()
        await super().async_will_remove_from_hass()

    async def restore_state(self) -> None:
        """Restores the state when the object is reloaded."""
        self.update_state()


class MagicBinarySensorEntity(MagicEntity, BinarySensorEntity):
    """Base class for the binary sensors to use in the system."""

    last_off_time = None
    _state = False
    _mode = "single"

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Create a new binary sensor entity."""
        MagicEntity.__init__(self, area)
        BinarySensorEntity.__init__(self, device_class)

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    def sensor_state_change(self, entity_id: str, from_state: State, to_state: State):
        """Actions when the sensor state has changed."""
        if not to_state:
            return

        self.logger.debug(
            "%s: sensor '%s' changed to {%s}",
            self.name,
            entity_id,
            to_state.state,
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state %s",
                self.name,
                entity_id,
                to_state.state,
            )
            return

        if to_state and to_state.state not in self.area.config.get(CONF_ON_STATES):
            self.last_off_time = datetime.now(datetime.UTC)  # Update last_off_time

        return self.update_state()

    def get_sensors_state(self, valid_states: list | None = None) -> int:
        """Get the current state of the sensor."""
        self.logger.debug(
            "[Area: %s] Updating state. (Valid states: %s)",
            self.area.slug,
            valid_states,
        )

        if valid_states is None:
            valid_states = [STATE_ON]

        active_sensors = []
        active_areas = set()

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        "[Area: %s] Could not get sensor state: %s entity not found, skipping",
                        self.area.slug,
                        sensor,
                    )
                    continue

                self.logger.debug(
                    "[Area: %s] Sensor %s state: %s",
                    self.area.slug,
                    sensor,
                    entity.state,
                )

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    self.logger.debug(
                        "[Area: %s] Sensor '%s' is unavailable, skipping.",
                        self.area.slug,
                        sensor,
                    )
                    continue

                if entity.state in valid_states:
                    self.logger.debug(
                        "[Area: %s] Valid presence sensor found: %s.",
                        self.area.slug,
                        sensor,
                    )
                    active_sensors.append(sensor)

            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    "[%s] Error getting entity state for '%s': %s",
                    self.area.slug,
                    sensor,
                    str(e),
                )

        self._attributes["active_sensors"] = active_sensors

        # Make a copy that doesn't gets cleared out, for debugging
        if active_sensors:
            self._attributes["last_active_sensors"] = active_sensors

        self.logger.debug(
            "[Area: %s] Active sensors: %s",
            self.area.slug,
            active_sensors,
        )

        if self.area.is_meta():
            active_areas = self.area.get_active_areas()
            self.logger.debug(
                "[Area: %s] Active areas: %s",
                self.area.slug,
                active_areas,
            )
            self._attributes["active_areas"] = active_areas

        if self._mode == "all":
            return len(active_sensors) == len(self.sensors)
        return len(active_sensors) > 0


class MagicSensorEntity(MagicEntity, SensorEntity):
    """Basic class for a magic sensor entity."""

    _mode = "mean"

    @property
    def state(self):
        """Return the state of the entity."""
        return self.get_sensors_state()

    def sensor_state_change(self, entity_id: str, from_state: State, to_state: State):
        """Call when the sensor state changes to update the system."""
        self.logger.debug(
            "%s: sensor '%s' changed to %s", self.name, entity_id, to_state.state
        )

        if to_state.state in INVALID_STATES:
            self.logger.debug(
                "%s: sensor '%s' has invalid state %s",
                self.name,
                entity_id,
                to_state.state,
            )
            return None

        return self.update_state()

    def get_sensors_state(self):
        """Get the current state of the sensor."""
        sensor_values = []

        # Loop over all entities and check their state
        for sensor in self.sensors:
            try:
                entity = self.hass.states.get(sensor)

                if not entity:
                    self.logger.info(
                        "[%s] Could not get sensor state: %s entity not found, skipping",
                        self.name,
                        sensor,
                    )
                    continue

                # Skip unavailable entities
                if entity.state in INVALID_STATES:
                    continue

            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    "[%s] Error getting entity state for '%s': %s",
                    self.name,
                    sensor,
                    str(e),
                )
                continue

            try:
                sensor_values.append(float(entity.state))
            except ValueError as e:
                err_str = str(e)
                self.logger.info(
                    "[%s] Non-numeric sensor value (%s) for entity {%s}, skipping",
                    self.name,
                    err_str,
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
    """A switch for use as a magic area, this controls the lights on/off and other things."""

    _state: str = STATE_OFF

    def __init__(self, area: MagicArea) -> None:
        """Initialize the system."""
        super().__init__(area)
        self._state = STATE_OFF

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state == STATE_ON

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""

        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(
                "Switch %s restored [state=%s]", self.name, last_state.state
            )
            self._state = last_state.state
        else:
            self._state = STATE_OFF

        self.schedule_update_ha_state()
        await super().async_added_to_hass()

    def turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._state = STATE_OFF
        self.schedule_update_ha_state()

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = STATE_ON
        self.schedule_update_ha_state()


class MagicLightGroup(MagicEntity, LightGroup):
    """Controls the lights with the specific setup."""

    def __init__(self, area: MagicArea, entities: list) -> None:
        """Create a new light group."""
        self._entities = entities

        self._name = f"{self.area.name} Lights"
        MagicEntity.__init__(self, area)
        LightGroup.__init__(
            self,
            unique_id=self.unique_id,
            name=self._name,
            entity_ids=self._entities,
            mode=False,
        )
