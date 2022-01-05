"""
This file is mostly https://github.com/daenny/climate_group,
adapted to work with Magic Areas.

Once this goes into the main Home Assistant code it will be phased out.
"""
import itertools
import logging
from collections import Counter
from typing import Any, Callable, Iterator, List, Optional

from homeassistant.components import climate
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity
from homeassistant.components.climate.const import *
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
)
from homeassistant.core import State, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change

from .base import MagicEntity
from .const import (
    AREA_STATE_CLEAR,
    CONF_CLIMATE_GROUPS_TURN_ON_STATE,
    CONF_FEATURE_CLIMATE_GROUPS,
    DATA_AREA_OBJECT,
    DEFAULT_CLIMATE_GROUPS_TURN_ON_STATE,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Climate Group"

# edit the supported_flags
SUPPORT_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE | SUPPORT_TARGET_TEMPERATURE_RANGE | SUPPORT_PRESET_MODE
)

# HVAC Action priority
HVAC_ACTIONS = [
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    None,
]


async def async_setup_entry(hass, config_entry, async_add_entities):

    ma_data = hass.data[MODULE_DATA]
    area_data = ma_data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Climate Groups
    if area.has_feature(CONF_FEATURE_CLIMATE_GROUPS):
        _LOGGER.debug(f"{area.name}: Setting up climate group")
        setup_climate_group(hass, area, async_add_entities)


def setup_climate_group(hass, area, async_add_entities):

    # Check if there are any lights
    if not area.has_entities(CLIMATE_DOMAIN):
        _LOGGER.debug(f"No {CLIMATE_DOMAIN} entities for area {area.name} ")
        return

    climate_entities = [e["entity_id"] for e in area.entities[CLIMATE_DOMAIN]]
    async_add_entities([AreaClimateGroup(hass, area, climate_entities)])


class ClimateGroup(ClimateEntity):
    """Representation of a climate group."""

    def __init__(
        self, name: str, entity_ids: List[str], excluded: List[str], unit: str
    ) -> None:
        """Initialize a climate group."""
        self._name = name  # type: str
        self._entity_ids = entity_ids  # type: List[str]
        if "c" in unit.lower():
            self._unit = TEMP_CELSIUS
        else:
            self._unit = TEMP_FAHRENHEIT
        self._min_temp = 0
        self._max_temp = 0
        self._current_temp = 0
        self._target_temp = 0
        # added the temp_low and temp_high
        self._target_temp_high = None
        self._target_temp_low = None
        self._mode = None
        self._action = None
        self._mode_list = None
        self._available = True  # type: bool
        self._supported_features = 0  # type: int
        self._async_unsub_state_changed = None
        self._preset_modes = None
        self._preset = None
        self._excluded = excluded

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        @callback
        def async_state_changed_listener(
            entity_id: str, old_state: State, new_state: State
        ):
            """Handle child updates."""
            self.async_schedule_update_ha_state(True)

        self._async_unsub_state_changed = async_track_state_change(
            self.hass, self._entity_ids, async_state_changed_listener
        )
        await self.async_update()

    async def async_will_remove_from_hass(self):
        """Handle removal from HASS."""
        if self._async_unsub_state_changed is not None:
            self._async_unsub_state_changed()
            self._async_unsub_state_changed = None

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def available(self) -> bool:
        """Return whether the climate group is available."""
        return self._available

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    @property
    def hvac_mode(self):
        """What is the thermostat intending to do"""
        return self._mode

    @property
    def hvac_action(self):
        """What is the thermostat _actually_ doing right now"""
        return self._action

    @property
    def hvac_modes(self):
        return self._mode_list

    @property
    def min_temp(self):
        return self._min_temp

    @property
    def max_temp(self):
        return self._max_temp

    @property
    def current_temperature(self):
        return self._current_temp

    @property
    def target_temperature(self):
        return self._target_temp

    # added the target_temperature_low and target_temperature_high
    @property
    def target_temperature_low(self):
        return self._target_temp_low

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def should_poll(self):
        """No polling needed for a climate group."""
        return False

    @property
    def should_poll(self):
        """No polling needed for a climate group."""
        return False

    @property
    def temperature_unit(self):
        """Return the unit of measurement that is used."""
        return self._unit

    @property
    def extra_state_attributes(self):
        """Return the state attributes for the climate group."""
        return {ATTR_ENTITY_ID: self._entity_ids}

    async def async_set_temperature(self, **kwargs):
        """Forward the turn_on command to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids}
        if ATTR_HVAC_MODE in kwargs:
            hvac_mode = kwargs.get(ATTR_HVAC_MODE)
            await self.async_set_hvac_mode(hvac_mode)
        # start add
        elif (
            ATTR_TEMPERATURE in kwargs
            or ATTR_TARGET_TEMP_LOW in kwargs
            or ATTR_TARGET_TEMP_HIGH in kwargs
        ):
            if ATTR_TEMPERATURE in kwargs:
                temperature = kwargs.get(ATTR_TEMPERATURE)
                data[ATTR_TEMPERATURE] = temperature
            elif ATTR_TARGET_TEMP_LOW in kwargs or ATTR_TARGET_TEMP_HIGH in kwargs:
                temperature_low = kwargs.get(ATTR_TARGET_TEMP_LOW)
                temperature_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
                data[climate.ATTR_TARGET_TEMP_LOW] = temperature_low
                data[climate.ATTR_TARGET_TEMP_HIGH] = temperature_high
            # end add
            await self.hass.services.async_call(
                climate.DOMAIN, climate.SERVICE_SET_TEMPERATURE, data, blocking=True
            )

    async def async_set_operation_mode(self, operation_mode):
        """Forward the turn_on command to all climate in the climate group. LEGACY CALL.
        This will be used only if the hass version is old."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_HVAC_MODE: operation_mode}

        await self.hass.services.async_call(
            climate.DOMAIN, climate.SERVICE_SET_HVAC_MODE, data, blocking=True
        )

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._preset

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return self._preset_modes

    async def async_set_hvac_mode(self, hvac_mode):
        """Forward the turn_on command to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_HVAC_MODE: hvac_mode}

        await self.hass.services.async_call(
            climate.DOMAIN, climate.SERVICE_SET_HVAC_MODE, data, blocking=True
        )

    async def async_update(self):
        """Query all members and determine the climate group state."""
        raw_states = [self.hass.states.get(x) for x in self._entity_ids]
        states = list(filter(None, raw_states))

        # if nothing is in excluded everything will be in 'filtered states'
        filtered_states = list(
            filter(
                lambda x: x.attributes.get(ATTR_PRESET_MODE, None)
                not in self._excluded,
                states,
            )
        )

        if not filtered_states:  # everything is being filtered, so show everything
            filtered_states = states

        _LOGGER.debug(f"Excluded by config: {self._excluded}")
        _LOGGER.debug(f"Resulting filtered states: {filtered_states}")

        all_modes = [x.state for x in filtered_states]
        # return the Mode (what the thermostat is set to do) in priority order (heat, cool, ...)
        self._mode = None
        # iterate through all hvac modes (skip first, as its off)
        for hvac_mode in HVAC_MODES[1:] + [HVAC_MODE_OFF]:
            # if any thermostat is in the given mode return it
            if any([mode == hvac_mode for mode in all_modes]):
                self._mode = hvac_mode
                break

        all_actions = [
            state.attributes.get(ATTR_HVAC_ACTION, None) for state in filtered_states
        ]
        for hvac_action in HVAC_ACTIONS:
            # if any thermostat is in the given action return it
            if any([action == hvac_action for action in all_actions]):
                self._action = hvac_action
                break

        # get the most common state of non-filtered devices
        all_presets = [
            state.attributes.get(ATTR_PRESET_MODE, None) for state in filtered_states
        ]
        self._preset = None
        if all_presets:
            # Report the most common preset_mode.
            self._preset = Counter(itertools.chain(all_presets)).most_common(1)[0][0]

        self._target_temp = _reduce_attribute(filtered_states, ATTR_TEMPERATURE)

        # start add
        self._target_temp_low = _reduce_attribute(filtered_states, ATTR_TARGET_TEMP_LOW)
        self._target_temp_high = _reduce_attribute(
            filtered_states, ATTR_TARGET_TEMP_HIGH
        )
        # end add

        self._current_temp = _reduce_attribute(
            filtered_states, ATTR_CURRENT_TEMPERATURE
        )

        _LOGGER.debug(
            f"Target temp: {self._target_temp}; Target temp low: {self._target_temp_low}; Target temp high: {self._target_temp_high}; Current temp: {self._current_temp}"
        )
        self._min_temp = _reduce_attribute(states, ATTR_MIN_TEMP, reduce=max)
        self._max_temp = _reduce_attribute(states, ATTR_MAX_TEMP, reduce=min)

        # Supported HVAC modes
        self._mode_list = None
        all_mode_lists = list(_find_state_attributes(states, ATTR_HVAC_MODES))
        if all_mode_lists:
            # Merge all effects from all effect_lists with a union merge.
            self._mode_list = list(set().union(*all_mode_lists))

        self._supported_features = 0
        for support in _find_state_attributes(states, ATTR_SUPPORTED_FEATURES):
            # Merge supported features by emulating support for every feature
            # we find.
            self._supported_features |= support
        # Bitwise-and the supported features with the Grouped climate's features
        # so that we don't break in the future when a new feature is added.
        self._supported_features &= SUPPORT_FLAGS

        self._preset_modes = None
        presets = []
        for preset in _find_state_attributes(states, ATTR_PRESET_MODES):
            presets.extend(preset)

        if len(presets):
            self._preset_modes = set(presets)
        _LOGGER.debug(
            f"State update complete. Supported: {self._supported_features}, mode: {self._mode}"
        )

    async def async_set_preset_mode(self, preset_mode: str):
        """Forward the preset_mode to all climate in the climate group."""
        data = {ATTR_ENTITY_ID: self._entity_ids, ATTR_PRESET_MODE: preset_mode}

        await self.hass.services.async_call(
            climate.DOMAIN, climate.SERVICE_SET_PRESET_MODE, data, blocking=True
        )


def _find_state_attributes(states: List[State], key: str) -> Iterator[Any]:
    """Find attributes with matching key from states."""
    for state in states:
        value = state.attributes.get(key)
        if value is not None:
            yield value


def _mean(*args):
    """Return the mean of the supplied values."""
    return sum(args) / len(args)


def _reduce_attribute(
    states: List[State],
    key: str,
    default: Optional[Any] = None,
    reduce: Callable[..., Any] = _mean,
) -> Any:
    """Find the first attribute matching key from states.
    If none are found, return default.
    """
    attrs = list(_find_state_attributes(states, key))

    if not attrs:
        return default

    if len(attrs) == 1:
        return attrs[0]

    return reduce(*attrs)


class AreaClimateGroup(MagicEntity, ClimateGroup):
    def __init__(self, hass, area, entities):

        name = f"Area Climate ({area.name})"

        self._name = name
        self._entities = entities

        self.hass = hass
        self.area = area

        unit = hass.config.units.temperature_unit

        ClimateGroup.__init__(self, self._name, self._entities, [], unit)

        _LOGGER.debug(
            f"Climate group {self._name} created with entities: {self._entities}"
        )

    def area_state_changed(self, area_id, states_tuple):

        if self.area.is_meta():
            _LOGGER.debug(f"{self.area.name} is meta. Noop.")
            return

        new_states, old_states = states_tuple

        if area_id != self.area.id:
            _LOGGER.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        _LOGGER.debug(f"Climate group {self.name} detected area state change")

        if AREA_STATE_CLEAR in new_states and self.hvac_mode != CURRENT_HVAC_OFF:
            _LOGGER.debug(
                f"{self.area.name}: Area clear, turning off Climate {self.entity_id}"
            )
            return self._turn_off()

        if self.area.is_occupied() and self.hvac_mode == CURRENT_HVAC_OFF:

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
                f"{self.area.name}: Area on {configured_state}, turning on Climate {self.entity_id}"
            )
            return self._turn_on()

    def _turn_off(self):

        service_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_HVAC_MODE: HVAC_MODE_OFF,
        }
        self.hass.services.call(CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, service_data)

    def _turn_on(self):

        for mode in (HVAC_MODE_HEAT_COOL, HVAC_MODE_HEAT, HVAC_MODE_COOL):
            if mode not in self.hvac_modes:
                continue

            service_data = {
                ATTR_ENTITY_ID: self.entity_id,
                ATTR_HVAC_MODE: mode,
            }

            self.hass.services.call(CLIMATE_DOMAIN, SERVICE_SET_HVAC_MODE, service_data)
            break

            self.set_hvac_mode(mode)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        if not self.area.is_meta():
            async_dispatcher_connect(
                self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
            )

        await super().async_added_to_hass()
