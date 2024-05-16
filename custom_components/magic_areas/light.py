"""Light controls for magic areas."""

import logging

from custom_components.magic_areas.base.entities import MagicLightGroup
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_SECONDARY_STATES,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
)
from custom_components.magic_areas.util import add_entities_when_ready
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_lights)


def add_lights(area: MagicArea, async_add_entities: AddEntitiesCallback):
    # Check feature availability
    if not area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        return

    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug(f"No {LIGHT_DOMAIN} entities for area {area.name} ")
        return

    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]

    light_groups = []

    # Create light groups
    if area.is_meta():
        light_groups.append(MagicLightGroup(area, light_entities))
    else:
        light_group_ids = []

        # Create extended light groups
        for category in LIGHT_GROUP_CATEGORIES:
            category_lights = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                category
            )

            if category_lights:
                _LOGGER.debug(
                    f"Creating {category} group for area {area.name} with lights: {category_lights}"
                )
                light_group_object = AreaLightGroup(area, category_lights, category)
                light_groups.append(light_group_object)

                # Infer light group entity id from name
                light_group_id = f"{LIGHT_DOMAIN}.{category.lower()}_{area.slug}"
                light_group_ids.append(light_group_id)

        _LOGGER.debug(
            f"Creating Area light group for area {area.name} with lights: {light_group_ids}"
        )
        light_groups.append(
            AreaLightGroup(
                area, light_entities, category=None, child_ids=light_group_ids
            )
        )

    # Create all groups
    async_add_entities(light_groups)


class AreaLightGroup(MagicLightGroup):
    """The light group to control the area lights specifically.

    One of these will be created for each type of light group, occupied,
    bright, sleep, accent, ...
    """

    def __init__(
        self, area, entities, dim_level, category=None, child_ids: list | None = None
    ) -> None:
        """Init the light group for the area."""
        MagicLightGroup.__init__(self, area, entities)

        if category:
            category_title = " ".join(category.split("_")).title()
            self._name = f"{category_title} ({self.area.name})"

        if child_ids is None:
            self._child_ids = []
        else:
            self._child_ids = child_ids

        self.category = category
        self.assigned_states = []
        self.act_on = []

        self.controlling = True
        self.controlled = False
        self.dim_level = dim_level

        self.init_group()

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
        self._attributes["lights"] = self._entities
        self._attributes["controlling"] = self.controlling

        if not self.category:
            self._attributes["child_ids"] = self._child_ids

        self.logger.debug(
            f"Light group {self._name} ({category}/{self._icon}) created with entities: {self._entities}"
        )

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    async def async_added_to_hass(self) -> None:
        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(f"{self.name} restored [state={last_state.state}]")
            self._state = last_state.state == STATE_ON

            if "controlling" in last_state.attributes.keys():
                controlling = last_state.attributes["controlling"]
                self.controlling = controlling
                self._attributes["controlling"] = self.controlling
        else:
            self._state = False

        self.schedule_update_ha_state()

        # Setup state change listeners
        await self._setup_listeners()

        await super().async_added_to_hass()

    async def _setup_listeners(self, _=None) -> None:
        async_dispatcher_connect(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self.area_state_changed
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [
                    self.entity_id,
                ],
                self.group_state_changed,
            )
        )

    """ State Change Handling """

    def area_state_changed(self, area_id, states_tuple):
        if area_id != self.area.id:
            self.logger.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        automatic_control = self.is_control_enabled()

        if not automatic_control:
            self.logger.debug(
                f"{self.name}: Automatic control for light group is disabled, skipping..."
            )
            return False

        self.logger.debug(f"Light group {self.name} detected area state change")

        # Handle all lights group
        if not self.category:
            return self.state_change_primary(states_tuple)

        # Handle light category
        return self.state_change_secondary(states_tuple)

    def state_change_primary(self, states_tuple):
        new_state, last_state = states_tuple

        # If area clear
        if AREA_STATE_CLEAR == new_state:
            self.logger.debug(f"{self.name}: Area is clear, should turn off lights!")
            self.reset_control()
            return self._turn_off()

        return False

    def state_change_secondary(self, states_tuple):
        new_state, last_state = states_tuple

        if AREA_STATE_CLEAR == new_state:
            self.logger.debug(
                f"{self.name}: Area is clear, reset control state and Noop!"
            )
            self.reset_control()
            return False

        # Do not handle lights that are not tied to a state
        if not self.assigned_states:
            self.logger.debug(f"{self.name}: No assigned states. Noop.")
            return False

        # Do not handle lights that are not in our state set.
        if not new_state in self.assigned_states:
            self.logger.debug(
                f"{self.name}: Not for this light group {self.assigned_states}. Noop."
            )
            return False

        self.logger.debug(
            f"Light group {self.name} assigned states: {self.assigned_states}. New state: {new_state} / Last state {last_state}"
        )

        return self._turn_on()

    def relevant_states(self):
        relevant_states = self.area.states.copy()

        if self.area.is_occupied():
            relevant_states.append(AREA_STATE_OCCUPIED)

        return relevant_states

    """ Light Handling """

    def _turn_on(self):
        if not self.controlling:
            return False

        if self.is_on and not self.force_on_occupied:
            return False

        self.controlled = True

        if self.dim_level == 0:
            self._turn_off()

        self.controlled = True
        service_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_BRIGHTNESS_PCT: self.dim_level,
        }
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _turn_off(self):
        if not self.controlling:
            return False

        if not self.is_on:
            return False

        self.controlled = True
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    """ Control Release """

    def is_control_enabled(self):
        entity_id = f"{SWITCH_DOMAIN}.area_light_control_{self.area.slug}"

        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self):
        self.controlling = True
        self._attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()
        self.logger.debug("{self.name}: Control Reset.")

    def is_child_controllable(self, entity_id):
        entity_object = self.hass.states.get(entity_id)
        if "controlling" in entity_object.attributes.keys():
            return entity_object.attributes["controlling"]

        return False

    def handle_group_state_change_primary(self):
        controlling = False

        for entity_id in self._child_ids:
            if self.is_child_controllable(entity_id):
                controlling = True
                break

        self.controlling = controlling
        self.schedule_update_ha_state()

    def handle_group_state_change_secondary(self):
        # If we changed last, unset
        if self.controlled:
            self.controlled = False
            self.logger.debug(f"{self.name}: Group controlled by us.")
        else:
            # If not, it was manually controlled, stop controlling
            self.controlling = False
            self.logger.debug(f"{self.name}: Group controlled by something else.")
            # Reset to non-occupied if occupied, so if the room is entered again
            # we control again.
            self.area.state = AREA_STATE_CLEAR

    def group_state_changed(self, event):
        # If area is not occupied, ignore
        if not self.area.is_occupied():
            self.reset_control()
        else:
            origin_event = event.context.origin_event

            if not self.category:
                self.handle_group_state_change_primary()
            else:
                # Ignore certain events
                if origin_event.event_type == "state_changed":
                    # Skip non ON/OFF state changes
                    if origin_event.data["old_state"].state not in [
                        STATE_ON,
                        STATE_OFF,
                    ]:
                        return False
                    if origin_event.data["new_state"].state not in [
                        STATE_ON,
                        STATE_OFF,
                    ]:
                        return False

                    # Skip restored events
                    if (
                        "restored" in origin_event.data["old_state"].attributes.keys()
                        and origin_event.data["old_state"].attributes["restored"]
                    ):
                        return False

                self.handle_group_state_change_secondary()

        # Update attribute
        self._attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()

        return True
