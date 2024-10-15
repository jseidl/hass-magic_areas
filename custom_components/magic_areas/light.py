"""Platform file for Magic Area's light entities."""

import asyncio
import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import (
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    DOMAIN as LIGHT_DOMAIN,
    SUPPORT_COLOR,
    SUPPORT_COLOR_TEMP,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import color as color_util

from .base.entities import MagicEntity
from .base.magic import MagicArea
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
    LightGroupCategory,
    MagicAreasFeatureInfoLightGroups,
)
from .util import cleanup_removed_entries, get_area_from_config_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the area light config entry."""

    area: MagicArea = get_area_from_config_entry(hass, config_entry)

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
                    "%s: Creating %s group for area with lights: %s",
                    area.name,
                    category,
                    category_lights,
                )
                light_group_object = AreaLightGroup(area, category_lights, category)
                light_groups.append(light_group_object)

                # Infer light group entity id from name
                light_group_id = f"{LIGHT_DOMAIN}.magic_areas_light_groups_{area.slug}_lights_{category.lower()}"
                light_group_ids.append(light_group_id)

        _LOGGER.debug(
            "%s: Creating Area light group for area with lights: %s",
            area.name,
            str(light_group_ids),
        )
        light_groups.append(
            AreaLightGroup(
                area,
                light_entities,
                category=LightGroupCategory.ALL,
                child_ids=light_group_ids,
            )
        )

    # Create all groups
    if light_groups:
        async_add_entities(light_groups)

    if LIGHT_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, light_groups, area.magic_entities[LIGHT_DOMAIN]
        )


class MagicLightGroup(MagicEntity, LightGroup):
    """Magic Light Group for Meta-areas."""

    feature_info = MagicAreasFeatureInfoLightGroups()

    def __init__(self, area, entities, translation_key: str | None = None):
        """Initialize parent class and state."""
        MagicEntity.__init__(
            self, area, domain=LIGHT_DOMAIN, translation_key=translation_key
        )
        LightGroup.__init__(
            self,
            name=None,
            unique_id=self.unique_id,
            entity_ids=entities,
            mode=False,
        )
        delattr(self, "_attr_name")

    def _get_active_lights(self) -> list[str]:
        """Return list of lights that are on."""
        active_lights = []
        for entity_id in self._entity_ids:
            light_state = self.hass.states.get(entity_id)
            if not light_state:
                continue
            if light_state.state == STATE_ON:
                active_lights.append(entity_id)

        return active_lights

    async def async_turn_on(self, **kwargs) -> None:
        """Forward the turn_on command to all lights in the light group."""
        data = kwargs.copy()

        # Get active lights or default to all lights
        active_lights = self._get_active_lights() or self._entity_ids

        # Get current brightness of the group
        group_state = self.hass.states.get(self.entity_id)
        current_brightness = (
            group_state.attributes.get("brightness", 0) if group_state else 0
        )

        # Desired brightness from data or default to max
        desired_brightness = data.get("brightness", 255)
        brightness_difference = desired_brightness - current_brightness

        service_calls = []

        for entity_id in active_lights:
            service_data = data.copy()
            state = self.hass.states.get(entity_id)
            if not state:
                continue

            support = state.attributes.get(ATTR_SUPPORTED_FEATURES, 0)

            # Adjust brightness
            if "brightness" in data:
                current_entity_brightness = state.attributes.get("brightness", 0)
                new_brightness = max(
                    1, min(255, current_entity_brightness + brightness_difference)
                )
                service_data["brightness"] = new_brightness

            # Handle color temperature and color support
            if support & SUPPORT_COLOR_TEMP and ATTR_COLOR_TEMP in service_data:
                temp_k = color_util.color_temperature_mired_to_kelvin(
                    service_data[ATTR_COLOR_TEMP]
                )
                hs_color = color_util.color_temperature_to_hs(temp_k)
                service_data[ATTR_HS_COLOR] = hs_color
                del service_data[ATTR_COLOR_TEMP]

            if not support & SUPPORT_COLOR:
                service_data.pop(ATTR_COLOR_TEMP, None)
                service_data.pop(ATTR_HS_COLOR, None)

            service_data[ATTR_ENTITY_ID] = entity_id
            service_calls.append(
                self.hass.services.async_call(
                    LIGHT_DOMAIN,
                    SERVICE_TURN_ON,
                    service_data,
                    blocking=True,
                    context=self._context,
                )
            )

        # Perform all service calls concurrently
        await asyncio.gather(*service_calls)


class AreaLightGroup(MagicLightGroup):
    """Magic Light Group."""

    def __init__(self, area, entities, category=None, child_ids=None):
        """Initialize light group."""

        MagicLightGroup.__init__(self, area, entities, translation_key=category)

        self._child_ids = child_ids

        self.category = category
        self.assigned_states = []
        self.act_on = []

        self.controlling = True
        self.controlled = False

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        if self.category != LightGroupCategory.ALL:
            self._icon = LIGHT_GROUP_ICONS.get(self.category, LIGHT_GROUP_DEFAULT_ICON)

        # Get assigned states
        if category != LightGroupCategory.ALL:
            self.assigned_states = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                LIGHT_GROUP_STATES[category], []
            )
            self.act_on = area.feature_config(CONF_FEATURE_LIGHT_GROUPS).get(
                LIGHT_GROUP_ACT_ON[category], DEFAULT_LIGHT_GROUP_ACT_ON
            )

        # Add static attributes
        self._attr_extra_state_attributes["lights"] = self._entity_ids
        self._attr_extra_state_attributes["controlling"] = self.controlling

        if self.category == LightGroupCategory.ALL:
            self._attr_extra_state_attributes["child_ids"] = self._child_ids

        self.logger.debug(
            "%s: Light group (%s) created with entities: %s",
            self.area.name,
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
                self._attr_extra_state_attributes["controlling"] = self.controlling
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
        if self.category == LightGroupCategory.ALL:
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
        entity_id = (
            f"{SWITCH_DOMAIN}.magic_areas_light_groups_{self.area.slug}_light_control"
        )

        switch_entity = self.hass.states.get(entity_id)

        if not switch_entity:
            return False

        return switch_entity.state.lower() == STATE_ON

    def reset_control(self):
        """Reset control status."""
        self.controlling = True
        self._attr_extra_state_attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()
        self.logger.debug("{self.name}: Control Reset.")

    def is_child_controllable(self, entity_id):
        """Check if child entity is controllable."""
        entity_object = self.hass.states.get(entity_id)
        if not entity_object:
            return False
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

            if self.category == LightGroupCategory.ALL:
                self.handle_group_state_change_primary()
            else:
                # Ignore certain events
                if origin_event.event_type == "state_changed":
                    # Skip non ON/OFF state changes
                    if (
                        "old_state" not in origin_event.data
                        or not origin_event.data["old_state"]
                        or not origin_event.data["old_state"].state
                        or origin_event.data["old_state"].state
                        not in [
                            STATE_ON,
                            STATE_OFF,
                        ]
                    ):
                        return False
                    if (
                        "new_state" not in origin_event.data
                        or not origin_event.data["new_state"]
                        or not origin_event.data["new_state"].state
                        or origin_event.data["new_state"].state
                        not in [
                            STATE_ON,
                            STATE_OFF,
                        ]
                    ):
                        return False

                    # Skip restored events
                    if (
                        "restored" in origin_event.data["old_state"].attributes
                        and origin_event.data["old_state"].attributes["restored"]
                    ):
                        return False

                self.handle_group_state_change_secondary()

        # Update attribute
        self._attr_extra_state_attributes["controlling"] = self.controlling
        self.schedule_update_ha_state()

        return True
