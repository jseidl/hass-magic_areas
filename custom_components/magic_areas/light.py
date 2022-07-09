DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity

from .base import MagicEntity
from .const import (
    AREA_PRIORITY_STATES,
    AREA_STATE_BRIGHT,
    AREA_STATE_CLEAR,
    AREA_STATE_DARK,
    AREA_STATE_OCCUPIED,
    CONF_FEATURE_LIGHT_GROUPS,
    DATA_AREA_OBJECT,
    DEFAULT_LIGHT_GROUP_ACT_ON,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LIGHT_GROUP_CATEGORIES,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
    LIGHT_GROUP_STATES,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    # Check feature availability
    if not area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        return

    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug(f"No {LIGHT_DOMAIN} entities for area {area.name} ")
        return

    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]

    light_groups = []

    # Create All light group
    _LOGGER.debug(
        f"Creating Area light group for area {area.name} with lights: {light_entities}"
    )
    if area.is_meta():
        light_groups.append(
            LightGroup(
                f"{area.slug}_lights", f"{area.name} Lights", light_entities, mode=False
            )
        )
    else:
        light_groups.append(AreaLightGroup(hass, area, light_entities))

        # Create extended light groups
        for category in LIGHT_GROUP_CATEGORIES:
            category_lights = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                category
            )

            if category_lights:
                _LOGGER.debug(
                    f"Creating {category} group for area {area.name} with lights: {category_lights}"
                )
                light_groups.append(
                    AreaLightGroup(hass, area, category_lights, category)
                )

    # Create all groups
    async_add_entities(light_groups)


class AreaLightGroup(MagicEntity, LightGroup, RestoreEntity):
    def __init__(self, hass, area, entities, category=None):

        name = f"{area.name} Lights"

        if category:
            category_title = " ".join(category.split("_")).title()
            name = f"{category_title} ({area.name})"

        self._name = name
        self._entities = entities

        self.hass = hass
        self.area = area
        self.category = category
        self.assigned_states = []
        self.act_on = []

        self._attributes = {}  # clear object

        LightGroup.__init__(
            self, self.unique_id, self._name, self._entities, mode=False
        )

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        if self.category:
            self._icon = LIGHT_GROUP_ICONS.get(self.category, LIGHT_GROUP_DEFAULT_ICON)

        # Get assigned states
        if category:
            self.assigned_states = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                LIGHT_GROUP_STATES[category], []
            )
            self.act_on = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                LIGHT_GROUP_ACT_ON[category], DEFAULT_LIGHT_GROUP_ACT_ON
            )

        # Add static attributes
        self._attributes["entity_id"] = self._entities

        _LOGGER.debug(
            f"Light group {self._name} ({category}/{self._icon}) created with entities: {self._entities}"
        )

    def is_control_enabled(self):

        entity_id = f"{SWITCH_DOMAIN}.area_light_control_{self.area.slug}"

        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_ON

    def relevant_states(self):

        relevant_states = self.area.states.copy()

        if self.area.is_occupied():
            relevant_states.append(AREA_STATE_OCCUPIED)

        if AREA_STATE_DARK in relevant_states:
            relevant_states.remove(AREA_STATE_DARK)

        return relevant_states

    def _turn_on(self):

        if self.is_on:
            return False

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _turn_off(self):

        if not self.is_on:
            return False

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    def state_change_primary(self, states_tuple):

        new_states, lost_states = states_tuple

        # If area clear
        if AREA_STATE_CLEAR in new_states:
            _LOGGER.debug(f"Area is clear, {self.name} SHOULD TURN OFF!")
            return self._turn_off()

        # If area has just went into AREA_STATE_BRIGHT state
        if self.area.has_state(AREA_STATE_BRIGHT) and AREA_STATE_BRIGHT in new_states:
            _LOGGER.debug(f"Area has AREA_STATE_BRIGHT, {self.name} SHOULD TURN OFF!")
            return self._turn_off()

        return False

    def state_change_secondary(self, states_tuple):

        new_states, lost_states = states_tuple

        # Only react to actual secondary state changes
        if not new_states and not lost_states:
            _LOGGER.debug(f"{self.name}: No new or lost states, noop.")
            return False

        # Do not handle lights that are not tied to a state
        if not self.assigned_states:
            _LOGGER.debug(f"{self.name}: No assigned states. Noop.")
            return False

        # If area clear, do nothing (main group will)
        if not self.area.is_occupied():
            _LOGGER.debug(f"Light group {self.name}: Area not occupied, ignoring.")
            return False

        # If area has AREA_STATE_DARK configured but it's not dark, do nothing (main group will)
        if self.area.has_configured_state(AREA_STATE_DARK) and not self.area.has_state(
            AREA_STATE_DARK
        ):
            _LOGGER.debug(
                f"{self.name}: Area has AREA_STATE_DARK entity but state not present, noop!"
            )
            return False

        _LOGGER.debug(
            f"Light group {self.name} assigned states: {self.assigned_states}. New states: {new_states} / Lost states {lost_states}"
        )

        # Calculate valid states (if area has states we listen to)
        # and check if area is under one or more priority state
        valid_states = [
            state for state in self.assigned_states if self.area.has_state(state)
        ]
        has_priority_states = any(
            [self.area.has_state(state) for state in AREA_PRIORITY_STATES]
        )
        non_priority_states = [
            state for state in valid_states if state not in AREA_PRIORITY_STATES
        ]

        _LOGGER.debug(
            f"{self.name} Has priority states? {has_priority_states}. Non-priority states: {non_priority_states}"
        )

        ## ACT ON Control
        # Do not act on occupancy change if not defined on act_on
        if (
            AREA_STATE_OCCUPIED in new_states
            and LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE not in self.act_on
        ):
            _LOGGER.debug(
                f"Area occupancy change detected but not configured to act on. Skipping."
            )
            return False

        # Do not act on state change if not defined on act_on
        if (
            AREA_STATE_OCCUPIED not in new_states
            and LIGHT_GROUP_ACT_ON_STATE_CHANGE not in self.act_on
        ):
            _LOGGER.debug(
                f"Area state change detected but not configured to act on. Skipping."
            )
            return False

        # Prefer priority states when present
        if has_priority_states:
            for non_priority_state in non_priority_states:
                valid_states.remove(non_priority_state)

        if valid_states:
            _LOGGER.debug(
                f"Area has valid states ({valid_states}), {self.name} SHOULD TURN ON!"
            )
            return self._turn_on()

        # Only turn lights off if not going into dark state
        if AREA_STATE_DARK in new_states:
            _LOGGER.debug(f"{self.name}: Entering {AREA_STATE_DARK} state, noop.")
            return False

        # Turn off if we're a PRIORITY_STATE and we're coming out of it
        out_of_priority_states = [
            state
            for state in AREA_PRIORITY_STATES
            if state in self.assigned_states and state in lost_states
        ]
        if out_of_priority_states:
            return self._turn_off()

        # Do not turn off if no new PRIORITY_STATES
        new_priority_states = [
            state for state in AREA_PRIORITY_STATES if state in new_states
        ]
        if not new_priority_states:
            _LOGGER.debug(f"{self.name}: No new priority states. Noop.")
            return False

        return self._turn_off()

    def area_state_changed(self, area_id, states_tuple):

        if area_id != self.area.id:
            _LOGGER.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        automatic_control = self.is_control_enabled()

        if not automatic_control:
            _LOGGER.debug(
                f"{self.name}: Automatic control for light group is disabled, skipping..."
            )
            return False

        _LOGGER.debug(f"Light group {self.name} detected area state change")

        # Handle all lights group
        if not self.category:
            return self.state_change_primary(states_tuple)

        # Handle light category
        return self.state_change_secondary(states_tuple)

    async def async_added_to_hass(self) -> None:

        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            _LOGGER.debug(f"{self.name} restored [state={last_state.state}]")
            self._state = last_state.state == STATE_ON
        else:
            self._state = False

        self.schedule_update_ha_state()

        # Register Callback

        async_dispatcher_connect(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
        )

        await super().async_added_to_hass()

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon
