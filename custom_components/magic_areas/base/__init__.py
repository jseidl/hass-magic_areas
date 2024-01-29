import logging

from datetime import timedelta
import voluptuous as vol

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)

from custom_components.magic_areas.const import (
    _DOMAIN_SCHEMA,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: _DOMAIN_SCHEMA},
    extra=vol.ALLOW_EXTRA,
)

class MagicEntity(RestoreEntity, Entity):

    area = None
    _name = None
    logger = None
    _attributes = {}

    def __init__(self, area):

        # Avoiding using super() due multiple inheritance issues
        Entity.__init__(self)
        RestoreEntity.__init__(self)

        self.logger = logging.getLogger(__name__)
        self._attributes = dict()
        self.area = area

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, f"magic_area_device_{self.area.id}")
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

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""
        if self.hass.is_running:
            await self._initialize()
        else:
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._initialize
            )

        await self.restore_state()

    async def restore_state(self):
        self.update_state()

class MagicSensorBase(MagicEntity):

    sensors = []
    _device_class = None

    def __init__(self, area, device_class):

        super().__init__(area)
        self.sensors = list()
        self._device_class = device_class

    @property
    def device_class(self):
        """Return the class of this binary_sensor."""
        return self._device_class

    def refresh_states(self, next_interval):
        self.logger.debug(f"Refreshing sensor states {self.name}")
        return self.update_state()

    def update_state(self):
        self._state = self.get_sensors_state()
        self.schedule_update_ha_state()

    async def _initialize(self, _=None) -> None:
        # Setup the listeners
        await self._setup_listeners()

    async def _shutdown(self) -> None:
        pass

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        await self._shutdown()

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

class AggregateBase(MagicSensorBase):
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