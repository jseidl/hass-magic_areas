"""Switches for magic areas."""

import logging

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import call_later
from homeassistant.util import slugify

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    ICON_LIGHT_CONTROL,
    ICON_PRESENCE_HOLD,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_switches)


def add_switches(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the swithces for the area."""
    if area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
        async_add_entities([AreaPresenceHoldSwitch(area)])

    async_add_entities(
        [AreaLightControlSwitch(area), AreaLightsManualOverrideActiveSwitch(area)]
    )


class SwitchBase(MagicEntity, SwitchEntity):
    """The base class for all the switches."""

    def __init__(self, area: MagicArea, translation_key: str) -> None:
        """Initialize the base switch bits, basic just a mixin for the two types."""
        MagicEntity.__init__(
            self, area=area, domain=SWITCH_DOMAIN, translation_key=translation_key
        )
        SwitchEntity.__init__(self)
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_should_poll = False
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()
        self.async_write_ha_state()
        self.schedule_update_ha_state()

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on presence hold."""
        self._attr_state = STATE_ON
        self._attr_is_on = True
        self.schedule_update_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off presence hold."""
        self._attr_state = STATE_OFF
        self._attr_is_on = False
        self.schedule_update_ha_state()


class AreaLightControlSwitch(SwitchBase):
    """Controls if the system is running and watching state."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area light control switch."""

        super().__init__(area, "light_control")
        self._attr_name = area.entity_name("Light Control")
        self.entity_id = area.entity_unique_id(SWITCH_DOMAIN, "Light Control")
        self._attr_state = STATE_OFF
        self._attr_is_on = False

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return ICON_LIGHT_CONTROL


class AreaLightsManualOverrideActiveSwitch(SwitchBase):
    """Keeps track of a manual override was enabled due to switch change."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area manual override switch."""

        super().__init__(area, "manual_override")
        self._attr_name = (
            f"Simply Magic Areas Manual Override Active ({self.area.name})"
        )
        self.entity_id = f"{SWITCH_DOMAIN}.{slugify(self._attr_name)}"
        self._attr_state = STATE_OFF
        self._attr_is_on = False

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return ICON_LIGHT_CONTROL


class AreaPresenceHoldSwitch(SwitchBase):
    """Control the presense/state from being changed for the device."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence hold switch."""

        super().__init__(area, "presence_hold")
        self._attr_name = f"Simply Magic Areas Presence Hold ({self.area.name})"
        self.entity_id = f"{SWITCH_DOMAIN}.{slugify(self._attr_name)}"

        self.timeout_callback = None
        self._attr_state = STATE_OFF
        self._attr_is_on = False

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return ICON_PRESENCE_HOLD

    def timeout_turn_off(self, next_interval):
        """Turn off the presence hold after the timeout."""
        if self._attr_state == STATE_ON:
            self.turn_off()

    async def async_turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._attr_state = STATE_ON
        self._attr_is_on = True
        self.schedule_update_ha_state()

        timeout = self.area.feature_config(CONF_FEATURE_PRESENCE_HOLD).get(
            CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
        )

        if timeout and not self.timeout_callback:
            self.timeout_callback = call_later(
                self.hass, timeout, self.timeout_turn_off
            )

    async def async_turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._attr_state = STATE_OFF
        self._attr_is_on = False
        self.schedule_update_ha_state()

        if self.timeout_callback:
            self.timeout_callback()
            self.timeout_callback = None
