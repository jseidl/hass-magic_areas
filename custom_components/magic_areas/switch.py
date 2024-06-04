"""Platform file for Magic Area's switch entities."""

import logging

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    CONF_FEATURE_CLIMATE_GROUPS,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_MEDIA_PLAYER_GROUPS,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_PRESENCE_HOLD_TIMEOUT,
    DEFAULT_PRESENCE_HOLD_TIMEOUT,
    ONE_MINUTE,
    MagicAreasFeatureInfoClimateGroups,
    MagicAreasFeatureInfoLightGroups,
    MagicAreasFeatureInfoMediaPlayerGroups,
    MagicAreasFeatureInfoPresenceHold,
)
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_switches)


def add_switches(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add all the switch entities for all features that have one."""

    switch_entities = []

    if area.has_feature(CONF_FEATURE_PRESENCE_HOLD):
        switch_entities.append(PresenceHoldSwitch(area))

    if area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        switch_entities.append(LightControlSwitch(area))

    if area.has_feature(CONF_FEATURE_MEDIA_PLAYER_GROUPS):
        switch_entities.append(MediaPlayerControlSwitch(area))

    if area.has_feature(CONF_FEATURE_CLIMATE_GROUPS):
        switch_entities.append(ClimateControlSwitch(area))

    if switch_entities:
        async_add_entities(switch_entities)

    if SWITCH_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, switch_entities, area.magic_entities[SWITCH_DOMAIN]
        )


class SwitchBase(MagicEntity, SwitchEntity):
    """The base class for all the switches."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the base switch bits, basic just a mixin for the two types."""
        MagicEntity.__init__(self, area, domain=SWITCH_DOMAIN)
        SwitchEntity.__init__(self)
        self._attr_device_class = SwitchDeviceClass.SWITCH
        self._attr_should_poll = False
        self._attr_is_on = False

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Restore state
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)

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


class ResettableSwitchBase(SwitchBase):
    """Control the presense/state from being changed for the device."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize the switch."""
        super().__init__(area)

        self._timeout_callback = None

        self.async_on_remove(self._clear_timers)

    def _clear_timers(self) -> None:
        """Remove the timer on entity removal."""
        if self._timeout_callback:
            self._timeout_callback()

    async def _timeout_turn_off(self, next_interval):
        """Turn off the presence hold after the timeout."""
        if self._attr_state == STATE_ON:
            await self.async_turn_off()

    async def async_turn_on(self, **kwargs):
        """Turn on presence hold."""
        self._attr_state = STATE_ON
        self._attr_is_on = True
        self.schedule_update_ha_state()

        timeout = self.area.feature_config(CONF_FEATURE_PRESENCE_HOLD).get(
            CONF_PRESENCE_HOLD_TIMEOUT, DEFAULT_PRESENCE_HOLD_TIMEOUT
        )

        if timeout and not self._timeout_callback:
            self._timeout_callback = async_call_later(
                self.hass, timeout * ONE_MINUTE, self._timeout_turn_off
            )

    async def async_turn_off(self, **kwargs):
        """Turn off presence hold."""
        self._attr_state = STATE_OFF
        self._attr_is_on = False
        self.schedule_update_ha_state()

        if self._timeout_callback:
            self._timeout_callback()
            self._timeout_callback = None


class ClimateControlSwitch(SwitchBase):
    """Switch to enable/disable climate control."""

    feature_info = MagicAreasFeatureInfoClimateGroups()


class LightControlSwitch(SwitchBase):
    """Switch to enable/disable light control."""

    feature_info = MagicAreasFeatureInfoLightGroups()


class MediaPlayerControlSwitch(SwitchBase):
    """Switch to enable/disable media player control."""

    feature_info = MagicAreasFeatureInfoMediaPlayerGroups()


class PresenceHoldSwitch(ResettableSwitchBase):
    """Switch to enable/disable presence hold."""

    feature_info = MagicAreasFeatureInfoPresenceHold()
