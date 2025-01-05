"""Platform file for Magic Area's climate entities.

This file is mostly https://github.com/bjrnptrsn/climate_group/,
adapted to work with Magic Areas.

Once this goes into the main Home Assistant code it will be phased out.
"""

from __future__ import annotations

import logging
from statistics import mean
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    ATTR_SWING_MODE,
    ATTR_SWING_MODES,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.group.entity import GroupEntity
from homeassistant.components.group.util import (
    find_state_attributes,
    most_frequent_attribute,
    reduce_attribute,
    states_equal,
)
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    AREA_STATE_CLEAR,
    CONF_CLIMATE_GROUPS_TURN_ON_STATE,
    CONF_FEATURE_CLIMATE_GROUPS,
    DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE,
    EMPTY_STRING,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    MagicAreasFeatureInfoClimateGroups,
)
from custom_components.magic_areas.helpers.area import get_area_from_config_entry
from custom_components.magic_areas.util import cleanup_removed_entries

# Climate Group Constants

SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.SWING_MODE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.TURN_ON
    | ClimateEntityFeature.TURN_OFF
)


def round_decimal_accuracy(
    value: float,
    fraction: int = 10,
    precision: int = 1,
) -> float:
    """Round the decimal part of a float to an fractional value with a certain precision."""
    fraction = max(min(fraction, 10), 1)
    precision = max(min(precision, 3), 1)

    return round(round(value * fraction) / fraction, precision)


# Magic Areas Constants

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Climate Group"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the area climate config entry."""

    area: MagicArea | None = get_area_from_config_entry(hass, config_entry)
    assert area is not None

    # Check feature availability
    if not area.has_feature(CONF_FEATURE_CLIMATE_GROUPS):
        return

    # Check if there are any climate entities
    if not area.has_entities(CLIMATE_DOMAIN):
        _LOGGER.debug("%s: No %s entities for area.", area.name, CLIMATE_DOMAIN)
        return

    climate_entities = [e["entity_id"] for e in area.entities[CLIMATE_DOMAIN]]

    climate_groups = [AreaClimateGroup(area, climate_entities)]

    if climate_groups:
        async_add_entities(climate_groups)

    if CLIMATE_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, climate_groups, area.magic_entities[CLIMATE_DOMAIN]
        )


# Climate Group class


class ClimateGroup(GroupEntity, ClimateEntity):
    """Representation of a climate group."""

    _attr_available: bool = False
    _attr_assumed_state: bool = True
    _enable_turn_on_off_backwards_compatibility: bool = False

    def __init__(
        self,
        *,
        unique_id: str | None,
        name: str,
        entity_ids: list[str],
        temperature_unit: str,
        decimal_accuracy_to_half: bool,
    ) -> None:
        """Initialize a climate group."""
        self._entity_ids = entity_ids

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_extra_state_attributes = {ATTR_ENTITY_ID: entity_ids}

        self._attr_temperature_unit = temperature_unit

        self._decimal_accuracy_to_half = decimal_accuracy_to_half

        self._logger_data = {ATTR_ENTITY_ID: entity_ids}

        # Set some defaults (will be overwritten on update)
        self._attr_supported_features = (
            ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        )
        self._attr_hvac_modes = [HVACMode.OFF]
        self._attr_hvac_mode = None
        self._attr_hvac_action = None
        self._most_common_hvac_mode = None

        self._attr_swing_modes = None
        self._attr_swing_mode = None

        self._attr_fan_modes = None
        self._attr_fan_mode = None

        self._attr_preset_modes = None
        self._attr_preset_mode = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        @callback
        def async_state_changed_listener(event: Event) -> None:
            """Handle child updates."""
            self.async_set_context(event.context)
            self.async_defer_or_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._entity_ids, async_state_changed_listener
            )
        )

        await super().async_added_to_hass()

    @callback
    def async_update_group_state(self) -> None:
        """Query all members and determine the climate group state."""
        self._attr_assumed_state = False

        states = [
            state
            for entity_id in self._entity_ids
            if (state := self.hass.states.get(entity_id)) is not None
        ]
        self._attr_assumed_state |= not states_equal(states)

        invalid_states = [STATE_UNAVAILABLE, STATE_UNKNOWN]
        filtered_states = list(
            filter(lambda state: state.state not in invalid_states, states)
        )

        # Set group as unavailable if all members are unavailable or missing
        self._attr_available = any(
            state.state not in invalid_states for state in states
        )

        # Temperature settings
        self._attr_target_temperature = reduce_attribute(
            states, ATTR_TEMPERATURE, reduce=lambda *data: mean(data)
        )
        if self._decimal_accuracy_to_half and self._attr_target_temperature is not None:
            self._attr_target_temperature = round_decimal_accuracy(
                value=self._attr_target_temperature, fraction=2, precision=1
            )

        self._attr_target_temperature_step = reduce_attribute(
            states, ATTR_TARGET_TEMP_STEP, reduce=max
        )

        self._attr_target_temperature_low = reduce_attribute(
            states, ATTR_TARGET_TEMP_LOW, reduce=lambda *data: mean(data)
        )
        self._attr_target_temperature_high = reduce_attribute(
            states, ATTR_TARGET_TEMP_HIGH, reduce=lambda *data: mean(data)
        )

        self._attr_current_temperature = reduce_attribute(
            states, ATTR_CURRENT_TEMPERATURE, reduce=lambda *data: mean(data)
        )

        self._attr_min_temp = reduce_attribute(states, ATTR_MIN_TEMP, reduce=max)
        self._attr_max_temp = reduce_attribute(states, ATTR_MAX_TEMP, reduce=min)
        # End temperature settings

        # available HVAC modes
        all_hvac_modes = list(find_state_attributes(states, ATTR_HVAC_MODES))
        if all_hvac_modes:
            # Merge all effects from all effect_lists with a union merge.
            self._attr_hvac_modes = list(set().union(*all_hvac_modes))

        # return the most common HVAC mode (what the thermostat is set to do) if state not invalid
        current_hvac_modes = [
            x.state for x in filtered_states if (x.state != HVACMode.OFF)
        ]
        if current_hvac_modes:
            most_common_hvac_mode = max(
                set(current_hvac_modes), key=current_hvac_modes.count
            )
            selected_hvac_mode = None
            if most_common_hvac_mode in HVACMode:
                selected_hvac_mode = HVACMode[most_common_hvac_mode.upper()]
            self._attr_hvac_mode = selected_hvac_mode
            if self._attr_hvac_mode != self._most_common_hvac_mode:
                self._most_common_hvac_mode = self._attr_hvac_mode
                _LOGGER.debug(
                    "Updated most common hvac mode: '%s', %s",
                    self._most_common_hvac_mode,
                    self._logger_data,
                )

        # return HVACMode.OFF if all modes are set to off
        elif all(x.state == HVACMode.OFF for x in filtered_states):
            self._attr_hvac_mode = HVACMode.OFF

        # else it's invalid
        else:
            self._attr_hvac_mode = None

        # return the most common action if it is not None
        hvac_actions = list(find_state_attributes(states, ATTR_HVAC_ACTION))
        if hvac_actions:
            current_hvac_actions = [a for a in hvac_actions if a != HVACAction.OFF]
            # return the most common action if it is not off
            if current_hvac_actions:
                self._attr_hvac_action = max(
                    set(current_hvac_actions), key=current_hvac_actions.count
                )
            # return HVACAction.OFF if all actions are set to off
            elif all(a == HVACAction.OFF for a in hvac_actions):
                self._attr_hvac_action = HVACAction.OFF
        # else it's None
        else:
            self._attr_hvac_action = None

        # available swing modes
        all_swing_modes = list(find_state_attributes(states, ATTR_SWING_MODES))
        if all_swing_modes:
            self._attr_swing_modes = list(set().union(*all_swing_modes))

        # Report the most common swing_mode.
        self._attr_swing_mode = most_frequent_attribute(states, ATTR_SWING_MODE)

        # available fan modes
        all_fan_modes = list(find_state_attributes(states, ATTR_FAN_MODES))
        if all_fan_modes:
            # Merge all effects from all effect_lists with a union merge.
            self._attr_fan_modes = list(set().union(*all_fan_modes))

        # Report the most common fan_mode.
        self._attr_fan_mode = most_frequent_attribute(states, ATTR_FAN_MODE)

        # available preset modes
        all_preset_modes = list(find_state_attributes(states, ATTR_PRESET_MODES))
        if all_preset_modes:
            # Merge all effects from all effect_lists with a union merge.
            self._attr_preset_modes = list(set().union(*all_preset_modes))

        # Report the most common fan_mode.
        self._attr_preset_mode = most_frequent_attribute(states, ATTR_PRESET_MODE)

        # Supported flags
        for support in find_state_attributes(states, ATTR_SUPPORTED_FEATURES):
            # Merge supported features by emulating support for every feature
            # we find.
            self._attr_supported_features |= support

        # Bitwise-and the supported features with the Grouped climate's features
        # so that we don't break in the future when a new feature is added.
        self._attr_supported_features &= SUPPORT_FLAGS

    async def async_turn_on(self) -> None:
        """Forward the turn_on command to all climate in the climate group."""
        if self._most_common_hvac_mode is not None:
            _LOGGER.info(
                "Turn on with most common hvac mode: '%s', %s",
                self._most_common_hvac_mode,
                self._logger_data,
            )
            await self.async_set_hvac_mode(self._most_common_hvac_mode)

        # Try to set the first available HVAC mode
        elif self._attr_hvac_modes:
            for mode in self._attr_hvac_modes:
                if mode != HVACMode.OFF:
                    _LOGGER.info(
                        "Turn on with first available hvac mode: '%s', %s",
                        mode,
                        self._logger_data,
                    )
                    await self.async_set_hvac_mode(mode)
                    break

        else:
            _LOGGER.warning(
                "Can't turn on: No hvac modes available, %s", self._logger_data
            )

    async def async_turn_off(self) -> None:
        """Forward the turn_off command to all climate in the climate group."""
        if HVACMode.OFF in self._attr_hvac_modes:
            _LOGGER.info("Turn off with hvac mode 'off' %s", self._logger_data)
            await self.async_set_hvac_mode(HVACMode.OFF)

        else:
            _LOGGER.warning(
                "Can't turn off: hvac mode 'off' not available, %s", self._logger_data
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Forward the set_temperature command to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids}

        if ATTR_HVAC_MODE in kwargs:
            await self.async_set_hvac_mode(kwargs[ATTR_HVAC_MODE])

        if ATTR_TEMPERATURE in kwargs:
            data[ATTR_TEMPERATURE] = kwargs[ATTR_TEMPERATURE]
        if ATTR_TARGET_TEMP_LOW in kwargs:
            data[ATTR_TARGET_TEMP_LOW] = kwargs[ATTR_TARGET_TEMP_LOW]
        if ATTR_TARGET_TEMP_HIGH in kwargs:
            data[ATTR_TARGET_TEMP_HIGH] = kwargs[ATTR_TARGET_TEMP_HIGH]

        _LOGGER.info("Setting temperature: %s", data)

        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Forward the set_hvac_mode command to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_HVAC_MODE: hvac_mode}
        _LOGGER.info("Setting hvac mode: %s", data)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Forward the set_fan_mode to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_FAN_MODE: fan_mode}
        _LOGGER.info("Setting fan mode: %s", data)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Forward the set_swing_mode to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_SWING_MODE: swing_mode}
        _LOGGER.info("Setting swing mode: %s", data)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_SWING_MODE,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Forward the set_preset_mode to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_PRESET_MODE: preset_mode}
        _LOGGER.info("Setting preset mode: %s", data)
        await self.hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_PRESET_MODE,
            data,
            blocking=True,
            context=self._context,
        )


# Magic Areas-specific code


class AreaClimateGroup(MagicEntity, ClimateGroup):
    """Climate group."""

    feature_info = MagicAreasFeatureInfoClimateGroups()

    def __init__(self, area, entities):
        """Initialize climate group."""
        MagicEntity.__init__(self, area, domain=CLIMATE_DOMAIN)

        self._entities = entities
        unit = self.area.hass.config.units.temperature_unit

        ClimateGroup.__init__(
            self,
            name=EMPTY_STRING,
            unique_id=self.unique_id,
            entity_ids=self._entities,
            temperature_unit=unit,
            decimal_accuracy_to_half=True,
        )
        delattr(self, "_attr_name")

        _LOGGER.debug(
            "%s: Climate group created with entities: %s",
            self.area.name,
            str(self._entities),
        )

    def _is_control_enabled(self):
        """Check if light climate is enabled by checking climate control switch state."""

        entity_id = f"{SWITCH_DOMAIN}.magic_areas_climate_groups_{self.area.slug}_climate_control"
        switch_entity = self.hass.states.get(entity_id)

        if not switch_entity:
            return False

        return switch_entity.state.lower() == STATE_ON

    def area_state_changed(self, area_id, states_tuple):
        """Handle area state change event."""
        if self.area.is_meta():
            _LOGGER.debug("%s: %s is meta. Noop.", self.name, self.area.name)
            return

        # Do nothing if control is disabled
        if not self._is_control_enabled():
            _LOGGER.debug("%s: Control disabled, skipping.", self.name)
            return

        # pylint: disable-next=unused-variable
        new_states, old_states = states_tuple

        if area_id != self.area.id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (req: %s}/self: %s)",
                self.name,
                area_id,
                self.area.id,
            )
            return

        _LOGGER.debug("%s: Climate group detected area state change.", self.name)

        if AREA_STATE_CLEAR in new_states and self._attr_hvac_action != HVACAction.OFF:
            _LOGGER.debug(
                "%s: Area %s clear, turning off climate.", self.name, self.area.name
            )
            return self._turn_off()

        if self.area.is_occupied() and self._attr_hvac_action == HVACAction.OFF:
            configured_state = self.area.feature_config(
                CONF_FEATURE_CLIMATE_GROUPS
            ).get(
                CONF_CLIMATE_GROUPS_TURN_ON_STATE, DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE
            )

            if (
                not self.area.has_state(configured_state)
                or configured_state not in new_states
            ):
                return

            _LOGGER.debug(
                "%s: Area %s on %s, turning on climate.",
                self.name,
                self.area.name,
                configured_state,
            )
            return self._turn_on()

    def _turn_off(self):
        """Turn off member entities."""
        service_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_HVAC_MODE: HVACMode.OFF,
        }
        self.hass.services.call(CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, service_data)

    def _turn_on(self):
        """Turn on member entities."""
        for mode in (HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL):
            if mode not in self._attr_hvac_modes:
                continue

            service_data = {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_HVAC_MODE: mode,
            }

            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, service_data)
            break

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        if not self.area.is_meta():
            async_dispatcher_connect(
                self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
            )

        await super().async_added_to_hass()
