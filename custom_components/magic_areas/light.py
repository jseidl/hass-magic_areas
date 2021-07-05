DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
)

from .base import MagicEntity
from .const import (
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    CONF_FEATURE_LIGHT_GROUPS,
    AREA_STATE_OCCUPIED,
    AREA_STATE_DARK,
    LIGHT_GROUP_CATEGORIES,
    LIGHT_GROUP_STATES,
    LIGHT_GROUP_ICONS,
    LIGHT_GROUP_DEFAULT_ICON,
    DATA_AREA_OBJECT,
    LIGHT_GROUP_CATEGORIES,
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

    if not light_entities:
        _LOGGER.debug(f"Not enough entities for Light group for area {area.name}")
        return

    light_groups = []

    # Create All light group
    _LOGGER.debug(
        f"Creating Area light group for area {area.name} with lights: {light_entities}"
    )
    light_groups.append(AreaLightGroup(hass, area, light_entities))

    # Create extended light groups
    for category in LIGHT_GROUP_CATEGORIES:
        category_lights = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(category)

        if category_lights:
            _LOGGER.debug(f"Creating {category} group for area {area.name} with lights: {category_lights}")
            light_groups.append(AreaLightGroup(hass, area, category_lights, category))

    # Create all groups
    async_add_entities(light_groups)

class AreaLightGroup(MagicEntity, LightGroup):

    def __init__(self, hass, area, entities, category = None):

        name = f"{area.name} Lights"

        if category:
            category_title = ' '.join(category.split('_')).title()
            name = f"{category_title} ({area.name})"

        self._name = name
        self._entities = entities

        self.hass = hass
        self.area = area
        self.category = category
        self.assigned_states = []

        LightGroup.__init__(self, self._name, self._entities)

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        if self.category:
            self._icon = LIGHT_GROUP_ICONS.get(self.category, LIGHT_GROUP_DEFAULT_ICON)

        # Get assigned states
        if category:
            self.assigned_states = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(LIGHT_GROUP_STATES[category])

        _LOGGER.debug(f"Light group {self._name} ({category}/{self._icon}) created with entities: {self._entities}")

    def relevant_states(self):

        relevant_states = self.area.secondary_states

        if self.area.is_occupied():
            relevant_states.append(AREA_STATE_OCCUPIED)

        if AREA_STATE_DARK in relevant_states:
            relevant_states.remove(AREA_STATE_DARK)

        return relevant_states

    def turn_on(self):

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def turn_off(self):
    
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    def state_change_primary(self):

        # If area clear
        if not self.area.is_occupied():
            _LOGGER.debug(f"Area is clear, {self.name} SHOULD TURN OFF!")
            return self.turn_off()

        # If area has AREA_STATE_DARK configured but it's not dark
        if self.area.has_configured_state(AREA_STATE_DARK) and not self.area.has_state(AREA_STATE_DARK):
            _LOGGER.debug(f"Area has AREA_STATE_DARK entity but state not present, {self.name} SHOULD TURN OFF!")
            return self.turn_off()

        # Get all light groups from config and check for someone 
        # listening to AREA_STATE_OCCUPIED
        # if someone is listening to this state, we should bail and let them have it
        for category in LIGHT_GROUP_CATEGORIES:
            # Check if light group is defined
            if self.area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(category):
                # Check light group states
                category_states = self.area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(LIGHT_GROUP_STATES[category])
                if AREA_STATE_OCCUPIED in category_states:
                    # Do nothing, category group will do
                    return False

        # If we don't, just turn on all of them
        return self.turn_on()

    def state_change_secondary(self):

        # If area clear, do nothing (main group will)
        if not self.area.is_occupied():
            _LOGGER.debug(f"Light group {self.name}: Area not occupied, ignoring.")
            return False

        # If area has AREA_STATE_DARK configured but it's not dark, do nothing (main group will)
        if self.area.has_configured_state(AREA_STATE_DARK) and not self.area.has_state(AREA_STATE_DARK):
            _LOGGER.debug(f"Area has AREA_STATE_DARK entity but state not present, {self.name} SHOULD TURN OFF!")
            return False

        _LOGGER.debug(f"Light group {self.name} assigned states: {self.assigned_states}")

        valid_states = []

        # Check if we should react
        for state in self.assigned_states:
            if self.area.has_state(state):
                valid_states.append(state)

        if AREA_STATE_OCCUPIED in valid_states and self.relevant_states() != [AREA_STATE_OCCUPIED]:
            valid_states.remove(AREA_STATE_OCCUPIED)

        if valid_states:
            _LOGGER.debug(f"Area has valid states ({valid_states}), {self.name} SHOULD TURN ON!")
            return self.turn_on()

        #if set(self.area.secondary_states) != set(AREA_STATE_OCCUPIED, AREA_STATE_DARK):
        _LOGGER.debug(f"Area doesn't have any valid states, {self.name} SHOULD TURN OFF!")
        return self.turn_off()

    def area_state_changed(self, area_id):

        if area_id != self.area.id:
            _LOGGER.debug(f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})")
            return

        _LOGGER.debug(f"Light group {self.name} detected area state change")

        # @TODO Handle all lights group
        if not self.category:
            return self.state_change_primary()

        # @TODO Handle light category
        return self.state_change_secondary()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        async_dispatcher_connect(self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed)

        await super().async_added_to_hass()

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon