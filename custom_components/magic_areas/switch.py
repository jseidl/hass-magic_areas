from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.event import call_later

from custom_components.magic_areas.base.primitives import SwitchBase
from custom_components.magic_areas.const import (
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    ICON_LIGHT_CONTROL,
    ICON_PRESENCE_HOLD,
)
from custom_components.magic_areas.util import add_entities_when_ready

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_switches)

def add_switches(area, async_add_entities):

    if area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
        async_add_entities([AreaPresenceHoldSwitch(area)])

    if area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        async_add_entities([AreaLightControlSwitch(area)])


class AreaLightControlSwitch(SwitchBase):
    def __init__(self, area):
        """Initialize the area light control switch."""

        super().__init__(area)
        self._name = f"Area Light Control ({self.area.name})"

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return ICON_LIGHT_CONTROL

class AreaPresenceHoldSwitch(SwitchBase):
    def __init__(self, area):
        """Initialize the area presence hold switch."""

        super().__init__(area)
        self._name = f"Area Presence Hold ({self.area.name})"
        
        self.timeout_callback = None

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return ICON_PRESENCE_HOLD

    def timeout_turn_off(self, next_interval):
        if self._state == STATE_ON:
            self.turn_off()

    def turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._state = STATE_ON
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
        self._state = STATE_OFF
        self.schedule_update_ha_state()

        if self.timeout_callback:
            self.timeout_callback()
            self.timeout_callback = None
