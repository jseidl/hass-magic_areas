DEPENDENCIES = ["magic_areas"]

import logging
from datetime import datetime, timedelta

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (
    STATE_ON,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.helpers.event import (
    async_track_state_change,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    MODULE_DATA,
    CONF_PRESENCE_HOLD_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

PRESENCE_HOLD_ICON = "mdi:car-brake-hold"


async def async_setup_platform(
    hass, config, async_add_entities, discovery_info=None
):  # pylint: disable=unused-argument

    areas = hass.data.get(MODULE_DATA)

    entities = []

    async_add_entities([AreaPresenceHoldSwitch(hass, area) for area in areas])


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    await async_setup_platform(hass, {}, async_add_entities)


class AreaPresenceHoldSwitch(SwitchEntity, RestoreEntity):
    def __init__(self, hass, area):
        """Initialize the area presence hold switch."""

        self.area = area
        self.hass = hass
        self._name = f"Area Presence Hold ({self.area.name})"
        self._state = False

        self.tracking_listeners = []

        _LOGGER.debug(f"Area {self.area.slug} presence hold switch initializing.")

        # Set attributes
        self._attributes = {}

        _LOGGER.info(f"Area {self.area.slug} presence hold switch initialized.")

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the attributes of the area."""
        return self._attributes

    @property
    def is_on(self):
        """Return true if the area is occupied."""
        return self._state

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return PRESENCE_HOLD_ICON

    async def async_added_to_hass(self):
        """Call when entity about to be added to hass."""

        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug(
                f"Presence hold switch restored: {self.area.slug} [{last_state.state}]"
            )
            self._state = last_state.state == STATE_ON
        else:
            self._state = False

        self.schedule_update_ha_state()

        self.schedule_update_ha_state()

    async def async_will_remove_from_hass(self):
        """Remove the listeners upon removing the component."""
        self._remove_listeners()

    def _remove_listeners(self):
        while self.tracking_listeners:
            remove_listener = self.tracking_listeners.pop()
            remove_listener()

    def turn_off_switch(self, next_interval):
        _LOGGER.debug(f"Reset presence hold switch {self.entity_id}")
        return self.turn_off()

    def reset_hold(self):
        reset_timeout = self.area.config.get(CONF_PRESENCE_HOLD_TIMEOUT)
        if reset_timeout:
            _LOGGER.debug(
                f"Will reset hold for {self.entity_id=} after {reset_timeout}s"
            )
            delta = timedelta(seconds=reset_timeout)
            self.tracking_listeners.append(
                async_track_time_interval(self.hass, self.turn_off_switch, delta)
            )

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = True
        self.schedule_update_ha_state()

        self.reset_hold()

    def turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._state = False
        self.schedule_update_ha_state()
        self._remove_listeners()
