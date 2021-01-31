DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.helpers.restore_state import RestoreEntity

from .base import MagicEntity
from .const import DATA_AREA_OBJECT, MODULE_DATA

_LOGGER = logging.getLogger(__name__)

PRESENCE_HOLD_ICON = "mdi:car-brake-hold"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""
    # await async_setup_platform(hass, {}, async_add_entities)
    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    async_add_entities([AreaPresenceHoldSwitch(hass, area)])


class AreaPresenceHoldSwitch(MagicEntity, SwitchEntity, RestoreEntity):
    def __init__(self, hass, area):
        """Initialize the area presence hold switch."""

        self.area = area
        self.hass = hass
        self._name = f"Area Presence Hold ({self.area.name})"
        self._state = False

        _LOGGER.debug(f"{self.name} Switch initializing.")

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

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = True
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._state = False
        self.schedule_update_ha_state()
