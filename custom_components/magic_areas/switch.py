DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.helpers.event import call_later
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import call_later

from .base import MagicEntity
from .const import (
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_PRESENCE_HOLD_TIMEOUT,
    DATA_AREA_OBJECT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

PRESENCE_HOLD_ICON = "mdi:car-brake-hold"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""
    # await async_setup_platform(hass, {}, async_add_entities)
    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    if area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
        async_add_entities([AreaPresenceHoldSwitch(hass, area)])


class AreaPresenceHoldSwitch(MagicEntity, SwitchEntity, RestoreEntity):
    def __init__(self, hass, area):
        """Initialize the area presence hold switch."""

        self.area = area
        self.hass = hass
        self._name = f"Area Presence Hold ({self.area.name})"
        self._state = False

        _LOGGER.debug(f"{self.name} Switch initializing.")

        self.timeout_callback = None

        # Set attributes
        self._attributes = {}

        _LOGGER.info(f"{self.name} Switch initialized.")

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
            _LOGGER.debug(f"Switch {self.name} restored [state={last_state.state}]")
            self._state = last_state.state == STATE_ON
        else:
            self._state = False

        self.schedule_update_ha_state()

    def timeout_turn_off(self, next_interval):

        if self._state:
            self.turn_off()

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = True
        self.schedule_update_ha_state()

        timeout = self.area.feature_config(CONF_FEATURE_PRESENCE_HOLD).get(
            CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
        )

        if timeout and not self.timeout_callback:
            self.timeout_callback = call_later(
                self.hass, timeout, self.timeout_turn_off
            )

    def turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._state = False
        self.schedule_update_ha_state()

        if self.timeout_callback:
            self.timeout_callback()
            self.timeout_callback = None
