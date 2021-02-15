DEPENDENCIES = ["magic_areas"]

import asyncio
import logging
from collections import Counter
import itertools
from typing import Any, Callable, Iterator, List, Optional, Tuple, cast

from homeassistant.components import light, group
from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_EFFECT_LIST,
    ATTR_FLASH,
    ATTR_HS_COLOR,
    ATTR_MAX_MIREDS,
    ATTR_MIN_MIREDS,
    ATTR_TRANSITION,
    ATTR_WHITE_VALUE,
    PLATFORM_SCHEMA,
    SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
    SUPPORT_EFFECT,
    SUPPORT_FLASH,
    SUPPORT_TRANSITION,
    SUPPORT_WHITE_VALUE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    CONF_NAME,
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
)
from homeassistant.core import CoreState, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, HomeAssistantType
from homeassistant.util import color as color_util
from homeassistant.util import slugify

# mypy: allow-incomplete-defs, allow-untyped-calls, allow-untyped-defs
# mypy: no-check-untyped-defs

from .base import MagicEntity
from .const import (
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CREATE_SUB_LIGHT_GROUPS,
    CONF_FEATURE_LIGHT_CONTROL,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_OVERHEAD_LIGHTS,
    CONF_ACCENT_LIGHTS,
    CONF_TASK_LIGHTS,
    CONF_SLEEP_LIGHTS,
    DATA_AREA_OBJECT,
    MODULE_DATA,
)


_LOGGER = logging.getLogger(__name__)


SUPPORT_GROUP_LIGHT = (
    SUPPORT_BRIGHTNESS
    | SUPPORT_COLOR_TEMP
    | SUPPORT_EFFECT
    | SUPPORT_FLASH
    | SUPPORT_COLOR
    | SUPPORT_TRANSITION
    | SUPPORT_WHITE_VALUE
)

# Prevent funny behaviour when lights are assigned to multiple categories
# Light in category key cannot be in any of the categories listed by value
LIGHT_PRECEDENCE = {
    CONF_SLEEP_LIGHTS: [],
    CONF_ACCENT_LIGHTS: [],
    CONF_TASK_LIGHTS: [CONF_ACCENT_LIGHTS],
    CONF_OVERHEAD_LIGHTS: [CONF_ACCENT_LIGHTS, CONF_TASK_LIGHTS],
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Check feature availability
    if (not area.has_feature(CONF_FEATURE_LIGHT_GROUPS)
            and not area.has_feature(CONF_FEATURE_LIGHT_CONTROL)):
        return

    # Check if there are any lights
    if not area.has_entities(light.DOMAIN):
        _LOGGER.debug(f"No {light.DOMAIN} entities for area {area.name} ")
        return

    # Check CONF_AGGREGATES_MIN_ENTITIES
    if (len(area.entities[light.DOMAIN]) < area.config.get(CONF_AGGREGATES_MIN_ENTITIES)
            and not area.has_feature(CONF_FEATURE_LIGHT_CONTROL)):
        _LOGGER.debug(f"Not enough entities for Light group for area {area.name}")
        return

    # Create Light Group
    _LOGGER.debug(
        f"Creating light group for area {area.name}"
    )
    area_light_group = AreaLightGroup(hass, area)
    light_groups = [area_light_group]

    # Create additional groups for different light categories in the area
    if area.config.get(CONF_CREATE_SUB_LIGHT_GROUPS):
        for light_category in LIGHT_PRECEDENCE.keys():
            lights_in_category = area_light_group.device_state_attributes.get(light_category)
            if lights_in_category:
                light_groups.append(AreaSubLightGroup(f"{area.name} {light_category.split('_')[0].title()} Lights", lights_in_category))

    async_add_entities(light_groups)


class AreaLightGroup(MagicEntity, group.GroupEntity, light.LightEntity):
    """Representation of a light group."""

    def __init__(self, hass, area) -> None:
        """Initialize a light group."""
        self.area = area
        self.hass = hass
        self._name = f"{self.area.name} Lights"
        self._attributes = {}

        lights_in_area = [e["entity_id"] for e in area.entities[light.DOMAIN]]

        # Filter out redundant assignments of lights to the categories in order to prevent funny
        # behaviour. Precedence of the categories is determined by LIGHT_PRECEDENCE.
        # These assignments must happen in this order to enable redundancy filtering to work.
        self._accent_lights = self._get_non_redundant_lights(area.config, CONF_ACCENT_LIGHTS)
        self._task_lights = self._get_non_redundant_lights(area.config, CONF_TASK_LIGHTS)
        self._overhead_lights = self._get_non_redundant_lights(area.config, CONF_OVERHEAD_LIGHTS, default=lights_in_area)
        self._sleep_lights = self._get_non_redundant_lights(area.config, CONF_SLEEP_LIGHTS, default=self._accent_lights)

        self._all_lights = list(
            set(self._overhead_lights + self._accent_lights + self._task_lights + self._sleep_lights))
        self._attributes[ATTR_ENTITY_ID] = self._all_lights

        self._any_light_on = False
        self._overhead_lights_on = False
        self._accent_lights_on = False
        self._task_lights_on = False
        self._sleep_lights_on = False
        self._available = False
        self._icon = "mdi:lightbulb-group"
        self._brightness: Optional[int] = None
        self._hs_color: Optional[Tuple[float, float]] = None
        self._color_temp: Optional[int] = None
        self._min_mireds: Optional[int] = 154
        self._max_mireds: Optional[int] = 500
        self._white_value: Optional[int] = None
        self._effect_list: Optional[List[str]] = None
        self._effect: Optional[str] = None
        self._supported_features: int = 0

    def _get_non_redundant_lights(self, area_config, light_category, default=[]):
        config_lights = area_config.get(light_category) or default.copy()

        def is_redundant(light):
            for precedent_category in LIGHT_PRECEDENCE[light_category]:
                if light in self._attributes.get(precedent_category, []):
                    if light_category == CONF_OVERHEAD_LIGHTS and not area_config.get(light_category):
                        # Don't warn, just debug as this is intended behaviour
                        _LOGGER.debug(f"{self.name}: Removing {light} from implicitly defined {light_category} because it is explicitly assigned to {precedent_category}")
                    else:
                        _LOGGER.warn(f"{self.name}: {light} defined both in {light_category} and {precedent_category}. Dropping it from {light_category}.")
                    return True
            return False

        filtered_lights = [light for light in config_lights if not is_redundant(light)]
        # Assign to attributes to enable next round of redundancy filtering
        self._attributes[light_category] = filtered_lights
        return filtered_lights

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        async def async_state_changed_listener(event):
            """Handle child updates."""
            self.async_set_context(event.context)
            await self.async_defer_or_update_ha_state()

        assert self.hass
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._all_lights, async_state_changed_listener
            )
        )

        if self.hass.state == CoreState.running:
            await self.async_update()
            return

        await super().async_added_to_hass()

    @property
    def state(self) -> str:
        """Return the state."""
        # Override state reporting because we modified is_on property
        return STATE_ON if self._any_light_on else STATE_OFF

    @property
    def is_on(self) -> bool:
        """Return the on/off state of the light group."""
        # Return state for overhead or sleep lights to enable more advanced toggle
        # (turning on overhead lights if only accent or task lights are on when toggling).
        # This is necessary because light.toggle service checks is_on and then calls
        # turn_on or turn_off service handlers, ignoring the toggle handler.
        # THIS DOES NOT REFLECT THE GROUP STATE REPORTED TO THE STATE MACHINE!
        return (
            self._any_light_on
            if self.area.is_sleeping()
            else self._overhead_lights_on
        )

    @property
    def available(self) -> bool:
        """Return whether the light group is available."""
        return self._available

    @property
    def icon(self):
        """Return the light group icon."""
        return self._icon

    @property
    def brightness(self) -> Optional[int]:
        """Return the brightness of this light group between 0..255."""
        return self._brightness

    @property
    def hs_color(self) -> Optional[Tuple[float, float]]:
        """Return the HS color value [float, float]."""
        return self._hs_color

    @property
    def color_temp(self) -> Optional[int]:
        """Return the CT color value in mireds."""
        return self._color_temp

    @property
    def min_mireds(self) -> Optional[int]:
        """Return the coldest color_temp that this light group supports."""
        return self._min_mireds

    @property
    def max_mireds(self) -> Optional[int]:
        """Return the warmest color_temp that this light group supports."""
        return self._max_mireds

    @property
    def white_value(self) -> Optional[int]:
        """Return the white value of this light group between 0..255."""
        return self._white_value

    @property
    def effect_list(self) -> Optional[List[str]]:
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self) -> Optional[str]:
        """Return the current effect."""
        return self._effect

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return self._supported_features

    def _get_lights_to_turn_on(self, params_given):

        if not self._any_light_on:
            # No lights are already on, select based on sleep entity and accent entity states
            if self._sleep_lights and self.area.is_sleeping():
                return self._sleep_lights
            elif self.area.is_accenting():
                return self._overhead_lights + self._accent_lights
            else:
                return self._overhead_lights
        elif params_given:
            # If there are any lights already on and specific parameters given, we only want
            # to act on the already turned on lights. This enables changing the brightness or
            # colortemp etc. only for the lights that are currently turned on, without turning
            # on additional lights.
            _LOGGER.debug(f"Only acting on already turned on lights because there are params given")
            return self._on_lights
        else:
            _LOGGER.debug("There are lights on but no params given. Assuming overhead lights shall be additionally turned on")
            if self._overhead_lights_on:
                _LOGGER.debug("Not acting on any lights because overhead lights are already on and without params it would do nothing")
                return []
            else:
                _LOGGER.debug("Turning on overhead lights because they were off and no params given (ignoring already turned on lights because they would not change without params")
                return self._overhead_lights

    async def async_turn_on(self, **kwargs):
        """Forward the turn_on command to all lights in the light group."""
        data = {}
        emulate_color_temp_entity_ids = []

        if ATTR_BRIGHTNESS in kwargs:
            data[ATTR_BRIGHTNESS] = kwargs[ATTR_BRIGHTNESS]

        if ATTR_HS_COLOR in kwargs:
            data[ATTR_HS_COLOR] = kwargs[ATTR_HS_COLOR]

        if ATTR_COLOR_TEMP in kwargs:
            data[ATTR_COLOR_TEMP] = kwargs[ATTR_COLOR_TEMP]

        if ATTR_WHITE_VALUE in kwargs:
            data[ATTR_WHITE_VALUE] = kwargs[ATTR_WHITE_VALUE]

        if ATTR_EFFECT in kwargs:
            data[ATTR_EFFECT] = kwargs[ATTR_EFFECT]

        if ATTR_TRANSITION in kwargs:
            data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        if ATTR_FLASH in kwargs:
            data[ATTR_FLASH] = kwargs[ATTR_FLASH]

        params_given = bool(data)
        lights_to_turn_on = self._get_lights_to_turn_on(params_given)

        _LOGGER.debug(f"Determined lights for turn_on (params_given={params_given}): {lights_to_turn_on}")

        data[ATTR_ENTITY_ID] = lights_to_turn_on

        if ATTR_COLOR_TEMP in data:
            # Create a new entity list to mutate
            updated_entities = lights_to_turn_on.copy()

            # Walk through initial entity ids, split entity lists by support
            for entity_id in lights_to_turn_on:
                state = self.hass.states.get(entity_id)
                if not state:
                    continue
                support = state.attributes.get(ATTR_SUPPORTED_FEATURES)
                # Only pass color temperature to supported entity_ids
                if bool(support & SUPPORT_COLOR) and not bool(
                    support & SUPPORT_COLOR_TEMP
                ):
                    emulate_color_temp_entity_ids.append(entity_id)
                    updated_entities.remove(entity_id)
                    data[ATTR_ENTITY_ID] = updated_entities

        if not emulate_color_temp_entity_ids:
            await self.hass.services.async_call(
                light.DOMAIN,
                light.SERVICE_TURN_ON,
                data,
                blocking=True,
                context=self._context,
            )
            return

        emulate_color_temp_data = data.copy()
        temp_k = color_util.color_temperature_mired_to_kelvin(
            emulate_color_temp_data[ATTR_COLOR_TEMP]
        )
        hs_color = color_util.color_temperature_to_hs(temp_k)
        emulate_color_temp_data[ATTR_HS_COLOR] = hs_color
        del emulate_color_temp_data[ATTR_COLOR_TEMP]

        emulate_color_temp_data[ATTR_ENTITY_ID] = emulate_color_temp_entity_ids

        await asyncio.gather(
            self.hass.services.async_call(
                light.DOMAIN,
                light.SERVICE_TURN_ON,
                data,
                blocking=True,
                context=self._context,
            ),
            self.hass.services.async_call(
                light.DOMAIN,
                light.SERVICE_TURN_ON,
                emulate_color_temp_data,
                blocking=True,
                context=self._context,
            ),
        )

    async def async_turn_off(self, **kwargs):
        """Forward the turn_off command to all lights in the light group."""
        data = {ATTR_ENTITY_ID: self._on_lights}

        if ATTR_TRANSITION in kwargs:
            data[ATTR_TRANSITION] = kwargs[ATTR_TRANSITION]

        await self.hass.services.async_call(
            light.DOMAIN,
            light.SERVICE_TURN_OFF,
            data,
            blocking=True,
            context=self._context,
        )

    async def async_update(self):
        """Query all members and determine the light group state."""
        all_states = [self.hass.states.get(x) for x in self._all_lights]
        states: List[State] = list(filter(None, all_states))
        on_states = [state for state in states if state.state == STATE_ON]

        self._on_lights = [e.entity_id for e in on_states]
        self._attributes["on_lights"] = self._on_lights

        self._any_light_on = len(on_states) > 0

        for light_category in ("overhead", "accent", "task", "sleep"):
            on_lights_in_category = [e for e in self._on_lights if e in getattr(self, f"_{light_category}_lights")]
            setattr(self, f"_{light_category}_on_lights", on_lights_in_category)
            self._attributes[f"{light_category}_on_lights"] = on_lights_in_category
            setattr(self, f"_{light_category}_lights_on", any(on_lights_in_category))
            self._attributes[f"{light_category}_lights_on"] = any(on_lights_in_category)

        self._available = any(state.state != STATE_UNAVAILABLE for state in states)

        self._brightness = _reduce_attribute(on_states, ATTR_BRIGHTNESS)

        self._hs_color = _reduce_attribute(on_states, ATTR_HS_COLOR, reduce=_mean_tuple)

        self._white_value = _reduce_attribute(on_states, ATTR_WHITE_VALUE)

        self._color_temp = _reduce_attribute(on_states, ATTR_COLOR_TEMP)
        self._min_mireds = _reduce_attribute(
            states, ATTR_MIN_MIREDS, default=154, reduce=min
        )
        self._max_mireds = _reduce_attribute(
            states, ATTR_MAX_MIREDS, default=500, reduce=max
        )

        self._effect_list = None
        all_effect_lists = list(_find_state_attributes(states, ATTR_EFFECT_LIST))
        if all_effect_lists:
            # Merge all effects from all effect_lists with a union merge.
            self._effect_list = list(set().union(*all_effect_lists))

        self._effect = None
        all_effects = list(_find_state_attributes(on_states, ATTR_EFFECT))
        if all_effects:
            # Report the most common effect.
            effects_count = Counter(itertools.chain(all_effects))
            self._effect = effects_count.most_common(1)[0][0]

        self._supported_features = 0
        for support in _find_state_attributes(states, ATTR_SUPPORTED_FEATURES):
            # Merge supported features by emulating support for every feature
            # we find.
            self._supported_features |= support
        # Bitwise-and the supported features with the GroupedLight's features
        # so that we don't break in the future when a new feature is added.
        self._supported_features &= SUPPORT_GROUP_LIGHT


def _find_state_attributes(states: List[State], key: str) -> Iterator[Any]:
    """Find attributes with matching key from states."""
    for state in states:
        value = state.attributes.get(key)
        if value is not None:
            yield value


def _mean_int(*args):
    """Return the mean of the supplied values."""
    return int(sum(args) / len(args))


def _mean_tuple(*args):
    """Return the mean values along the columns of the supplied values."""
    return tuple(sum(x) / len(x) for x in zip(*args))


def _reduce_attribute(
    states: List[State],
    key: str,
    default: Optional[Any] = None,
    reduce: Callable[..., Any] = _mean_int,
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


class AreaSubLightGroup(LightGroup):
    def __init__(self, name, entities):
        super().__init__(name, entities)

    @property
    def unique_id(self):
        """Return a unique ID."""
        name_slug = slugify(self.name)
        return f"magic_areas_entity_{name_slug}"
