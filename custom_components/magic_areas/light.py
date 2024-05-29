"""Platform file for Magic Area's light entities."""

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import slugify

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .const import (
    AREA_PRIORITY_STATES,
    AREA_STATE_BRIGHT,
    AREA_STATE_CLEAR,
    AREA_STATE_DARK,
    AREA_STATE_OCCUPIED,
    CONF_FEATURE_LIGHT_GROUPS,
    DEFAULT_LIGHT_GROUP_ACT_ON,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    LIGHT_GROUP_ACT_ON,
    LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE,
    LIGHT_GROUP_ACT_ON_STATE_CHANGE,
    LIGHT_GROUP_CATEGORIES,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
    LIGHT_GROUP_STATES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_lights)


def add_lights(area, async_add_entities):
    """Add all the light entities for all features that have one."""
    # Check feature availability
    if not area.has_feature(CONF_FEATURE_LIGHT_GROUPS):
        return

    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug("%s: No %s entities for area.", area.name, LIGHT_DOMAIN)
        return

    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]

    light_groups = []

    # Create light groups
    if area.is_meta():
        meta_area_name = f"{area.name} Lights"
        light_groups.append(
            LightGroup(
                name=meta_area_name,
                unique_id=slugify(meta_area_name),
                entity_ids=light_entities,
                mode=False,
            )
        )
    else:
        light_group_ids = []

        # Create extended light groups
        for category in LIGHT_GROUP_CATEGORIES:
            category_lights = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                category
            )

            if category_lights:
                _LOGGER.debug(
                    "%s: Creating %s group for area with lights: %s",
                    area.name,
                    category,
                    category_lights,
                )
                light_group_object = AreaLightGroup(area, category_lights, category)
                light_groups.append(light_group_object)

                # Infer light group entity id from name
                light_group_id = f"{LIGHT_DOMAIN}.{category.lower()}_{area.slug}"
                light_group_ids.append(light_group_id)

        _LOGGER.debug(
            "%s: Creating Area light group for area with lights: %s",
            area.name,
            str(light_group_ids),
        )
        light_groups.append(
            AreaLightGroup(
                area, light_entities, category=None, child_ids=light_group_ids
            )
        )

    # Create all groups
    async_add_entities(light_groups)


class AreaLightGroup(MagicEntity, LightGroup):
    """Magic Light Group."""

    def __init__(self, area, entities, category=None, child_ids=None):
        """Initialize light group."""

        name = f"{area.name} Lights"

        if not child_ids:
            child_ids = []

        if category:
            category_title = " ".join(category.split("_")).title()
            name = f"{category_title} ({area.name})"

        self._child_ids = child_ids

        self.category = category
        self.assigned_states = []
        self.act_on = []

        self.controlling = True
        self.controlled = False

        MagicEntity.__init__(self, area)
        LightGroup.__init__(
            self,
            entity_ids=entities,
            name=name,
            unique_id=slugify(name),
            mode=False,
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
        self._attributes["lights"] = self._entity_ids
        self._attributes["controlling"] = self.controlling

        if not self.category:
            self._attributes["child_ids"] = self._child_ids

        self.logger.debug(
            "%s: Light group (%s) created with entities: %s",
            self.name,
            category,
            str(self._entity_ids),
        )

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        return self._icon

    async def async_added_to_hass(self) -> None:
        """Restore state and setup listeners."""
        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(
                "%s: State restored [state=%s]", self.name, last_state.state
            )
            self._attr_is_on = last_state.state == STATE_ON

            if "controlling" in last_state.attributes:
                controlling = last_state.attributes["controlling"]
                self.controlling = controlling
                self._attributes["controlling"] = self.controlling
        else:
            self._attr_is_on = False

        self.schedule_update_ha_state()

        # Setup state change listeners
        await self._setup_listeners()

        await super().async_added_to_hass()

    async def _setup_listeners(self, _=None) -> None:
        """Set up listeners for area state chagne."""
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

    # State Change Handling

    def area_state_changed(self, area_id, states_tuple):
        """Handle area state change event."""
        if area_id != self.area.id:
            self.logger.debug(
                "%s: Area state change event not for us. Skipping. (req: %s/self: %s)",
                self.name,
                area_id,
                self.area.id,
            )
            return

        automatic_control = self.is_control_enabled()

        if not automatic_control:
            self.logger.debug(
                "%s: Automatic control for light group is disabled, skipping...",
                self.name,
            )
            return False

        self.logger.debug("%s: Light group detected area state change", self.name)

        # Handle all lights group
        if not self.category:
            return self.state_change_primary(states_tuple)

        # Handle light category
        return self.state_change_secondary(states_tuple)

    def state_change_primary(self, states_tuple):
        """Handle primary state change."""
        # pylint: disable-next=unused-variable
        new_states, lost_states = states_tuple

        # If area clear
        if AREA_STATE_CLEAR in new_states:
            self.logger.debug("%s: Area is clear, should turn off lights!", self.name)
            self.reset_control()
            return self._turn_off()

        return False

    def state_change_secondary(self, states_tuple):
        """Handle secondary state change."""
        new_states, lost_states = states_tuple

        if AREA_STATE_CLEAR in new_states:
            self.logger.debug(
                "%s: Area is clear, reset control state and Noop!", self.name
            )
            self.reset_control()
            return False

        if self.area.has_state(AREA_STATE_BRIGHT):
            # Only turn off lights when bright if the room was already occupied
            if (
                AREA_STATE_BRIGHT in new_states
                and AREA_STATE_OCCUPIED not in new_states
            ):
                self.controlled = True
                self._turn_off()
            return False

        # Only react to actual secondary state changes
        if not new_states and not lost_states:
            self.logger.debug("%s: No new or lost states, noop.", self.name)
            return False

        # Do not handle lights that are not tied to a state
        if not self.assigned_states:
            self.logger.debug("%s: No assigned states. noop.", self.name)
            return False

        # If area clear, do nothing (main group will)
        if not self.area.is_occupied():
            self.logger.debug("%s: Area not occupied, ignoring.", self.name)
            return False

        self.logger.debug(
            "%s: Assigned states: %s. New states: %s / Lost states %s",
            self.name,
            str(self.assigned_states),
            str(new_states),
            str(lost_states),
        )

        # Calculate valid states (if area has states we listen to)
        # and check if area is under one or more priority state
        valid_states = [
            state for state in self.assigned_states if self.area.has_state(state)
        ]
        has_priority_states = any(
            self.area.has_state(state) for state in AREA_PRIORITY_STATES
        )
        non_priority_states = [
            state for state in valid_states if state not in AREA_PRIORITY_STATES
        ]

        self.logger.debug(
            "%s: Has priority states? %s. Non-priority states: %s",
            self.name,
            has_priority_states,
            str(non_priority_states),
        )

        # ACT ON Control
        # Do not act on occupancy change if not defined on act_on
        if (
            AREA_STATE_OCCUPIED in new_states
            and LIGHT_GROUP_ACT_ON_OCCUPANCY_CHANGE not in self.act_on
        ):
            self.logger.debug(
                "Area occupancy change detected but not configured to act on. Skipping."
            )
            return False

        # Do not act on state change if not defined on act_on
        if (
            AREA_STATE_OCCUPIED not in new_states
            and LIGHT_GROUP_ACT_ON_STATE_CHANGE not in self.act_on
        ):
            self.logger.debug(
                "Area state change detected but not configured to act on. Skipping."
            )
            return False

        # Prefer priority states when present
        if has_priority_states:
            for non_priority_state in non_priority_states:
                valid_states.remove(non_priority_state)

        if valid_states:
            self.logger.debug(
                "%s: Area has valid states (%s), Group should turn on!",
                self.name,
                str(valid_states),
            )
            self.controlled = True
            return self._turn_on()

        # Only turn lights off if not going into dark state
        if AREA_STATE_DARK in new_states:
            self.logger.debug(
                "%s: Entering %s state, noop.", self.name, AREA_STATE_DARK
            )
            return False

        # Turn off if we're a PRIORITY_STATE and we're coming out of it
        out_of_priority_states = [
            state
            for state in AREA_PRIORITY_STATES
            if state in self.assigned_states and state in lost_states
        ]
        if out_of_priority_states:
            self.controlled = True
            return self._turn_off()

        # Do not turn off if no new PRIORITY_STATES
        new_priority_states = [
            state for state in AREA_PRIORITY_STATES if state in new_states
        ]
        if not new_priority_states:
            self.logger.debug("%s: No new priority states. Noop.", self.name)
            return False

        self.controlled = True
        return self._turn_off()

    def relevant_states(self):
        """Return relevant states and remove irrelevant ones (opinionated)."""
        relevant_states = self.area.states.copy()

        if self.area.is_occupied():
            relevant_states.append(AREA_STATE_OCCUPIED)

        if AREA_STATE_DARK in relevant_states:
            relevant_states.remove(AREA_STATE_DARK)

        return relevant_states

    # Light Handling

    def _turn_on(self):
        """Turn on light if it's not already on and if we're controlling it."""
        if not self.controlling:
            return False

        if self.is_on:
            return False

        self.controlled = True

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def _turn_off(self):
        """Turn off light if it's not already off and we're controlling it."""
        if not self.controlling:
            return False

        if not self.is_on:
            return False

        service_data = {ATTR_ENTITY_ID: self.entity_id}
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    # Control Release

    def is_control_enabled(self):
        """Check if light control is enabled by checking light control switch state."""
        entity_id = f"{SWITCH_DOMAIN}.area_light_control_{self.area.slug}"

        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self):
        """Reset control status."""
        self.controlling = True
        self._attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()
        self.logger.debug("{self.name}: Control Reset.")

    def is_child_controllable(self, entity_id):
        """Check if child entity is controllable."""
        entity_object = self.hass.states.get(entity_id)
        if "controlling" in entity_object.attributes:
            return entity_object.attributes["controlling"]

        return False

    def handle_group_state_change_primary(self):
        """Handle group state change for primary area state events."""
        controlling = False

        for entity_id in self._child_ids:
            if self.is_child_controllable(entity_id):
                controlling = True
                break

        self.controlling = controlling
        self.schedule_update_ha_state()

    def handle_group_state_change_secondary(self):
        """Handle group state change for secondary area state events."""
        # If we changed last, unset
        if self.controlled:
            self.controlled = False
            self.logger.debug("%s: Group controlled by us.", self.name)
        else:
            # If not, it was manually controlled, stop controlling
            self.controlling = False
            self.logger.debug("%s: Group controlled by something else.", self.name)

    def group_state_changed(self, event):
        """Handle group state change events."""
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
                        "restored" in origin_event.data["old_state"].attributes
                        and origin_event.data["old_state"].attributes["restored"]
                    ):
                        return False

                self.handle_group_state_change_secondary()

        # Update attribute
        self._attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()

        return True
