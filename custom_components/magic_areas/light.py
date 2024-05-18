"""Light controls for magic areas."""

import logging
import traceback
from typing import Any
import pdb

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicLightGroup
from .base.magic import MagicArea
from .const import (
    ALL_LIGHT_ENTITIES,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    EVENT_MAGICAREAS_AREA_STATE_CHANGED,
    LIGHT_GROUP_DEFAULT_ICON,
    LIGHT_GROUP_ICONS,
    AreaState,
)

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, _add_lights)


def _add_lights(area: MagicArea, async_add_entities: AddEntitiesCallback):
    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug("No %s entities for area %s ", LIGHT_DOMAIN, area.name)
        return

    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]

    light_groups = []

    # Create light groups
    if area.is_meta():
        light_groups.append(MagicLightGroup(area, light_entities))
    else:
        light_group_ids = []

        # Create extended light groups
        for lg in ALL_LIGHT_ENTITIES:
            light_entity = area.config.get(lg.entity_name(), None)
            category_lights = area.config.get(lg.lights_to_control(), light_entities)
            _LOGGER.debug(
                "Creating %s group for area %s with lights: %s",
                lg.name,
                area.name,
                category_lights,
            )
            # Create the ones with no entity automatically plus ones with an entity set
            if not lg.has_entity or light_entity is not None:
                light_group_object = AreaLightGroup(area, category_lights, lg.name)
                light_groups.append(light_group_object)

                # Infer light group entity id from name
                light_group_id = f"{LIGHT_DOMAIN}.{lg.name.lower()}_{area.slug}"
                light_group_ids.append(light_group_id)

    # Create all groups
    async_add_entities(light_groups)


class AreaLightGroup(MagicLightGroup):
    """The light group to control the area lights specifically.

    One of these will be created for each type of light group, occupied,
    bright, sleep, accent, ...
    """

    def __init__(
        self,
        area: MagicArea,
        entities: list[str],
        category: str | None = None,
        child_ids: list[str] | None = None,
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

        self._set_controlled_by_this_entity(True)

        self._icon = LIGHT_GROUP_DEFAULT_ICON

        if self.category:
            self._icon = LIGHT_GROUP_ICONS.get(self.category, LIGHT_GROUP_DEFAULT_ICON)

        # Get assigned states
        self.dim_level = 0.0
        if category:
            self.light_conf = self.area.state_config(self.category)
            self.act_on = self.area.feature_config(
                CONF_FEATURE_ADVANCED_LIGHT_GROUPS
            ).get(self.light_conf.advanced_act_on(), [])
            self.assigned_states = area.feature_config(
                CONF_FEATURE_ADVANCED_LIGHT_GROUPS
            ).get(
                self.light_conf.advanced_activate_states(),
                [self.light_conf.enable_state],
            )
            self.dim_level = float(
                self.area.config.get(self.light_conf.state_dim_level(), 100)
            )

        # Add static attributes
        self.last_update_from_entity = False
        self._attributes["lights"] = self._entity_ids
        self._attributes["last_update_from_entity"] = False

        if not self.category:
            self._attributes["child_ids"] = self._child_ids

        self.logger.debug(
            "Light group %s (%s/%s) created with entities: %s",
            self.name,
            category,
            self._icon,
            self._entity_ids,
        )

    @property
    def icon(self) -> str:
        """Return the icon to be used for this entity."""
        return self._icon

    async def async_added_to_hass(self) -> None:
        """Run when this is added into hass."""
        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(
                "%s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON

            if "last_update_from_entity" in last_state.attributes:
                self.last_update_from_entity = last_state.attributes[
                    "last_update_from_entity"
                ]
                self._attributes["last_update_from_entity"] = (
                    self.last_update_from_entity
                )
            else:
                self._set_controlled_by_this_entity(True)
        else:
            self._attr_is_on = False

        self.schedule_update_ha_state()

        # Setup state change listeners
        await self._setup_listeners()

        await super().async_added_to_hass()

    async def _setup_listeners(self, _=None) -> None:
        async_dispatcher_connect(
            self.hass, EVENT_MAGICAREAS_AREA_STATE_CHANGED, self._area_state_changed
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [
                    self.entity_id,
                ],
                self._group_state_changed,
            )
        )

    ### State Change Handling

    def _area_state_changed(self, area_id: str, states_tuple: (str, str)) -> None:
        if area_id != self.area.id:
            self.logger.debug(
                f"Area state change event not for us. Skipping. (req: {area_id}/self: {self.area.id})"
            )
            return

        automatic_control = self.is_control_enabled()

        if not automatic_control:
            self.logger.debug(
                "%s: Automatic control for light group is disabled, skipping", self.name
            )
            return False

        self.logger.debug("Light group %s detected area state change", self.name)

        # Handle all lights group
        if not self.category:
            return self._state_change_primary(states_tuple)

        # Handle light category
        return self._state_change_secondary(states_tuple)

    def _state_change_primary(self, states_tuple: (str, str)) -> bool:
        new_state, last_state = states_tuple

        # If area clear
        if new_state == AreaState.AREA_STATE_CLEAR:
            self.logger.debug("%s: Area is clear, should turn off lights!", self.name)
            self._reset_control()
            return self._turn_off()

        return False

    def _state_change_secondary(self, states_tuple: (str, str)) -> bool:
        new_state, last_state = states_tuple

        if new_state == AreaState.AREA_STATE_CLEAR:
            self.logger.debug(
                "%s: Area is clear, reset control state and Noop!", self.name
            )
            self._reset_control()
            return False

        # Do not handle lights that are not tied to a state
        if not self.assigned_states:
            self.logger.debug("%s: No assigned states. Noop", self.name)
            return False

        # Do not handle lights that are not in our state set.
        if new_state not in self.assigned_states:
            self.logger.debug(
                "%s: Not for this light group %s. Noop.",
                self.name,
                self.assigned_states,
            )
            return False

        self.logger.debug(
            "Light group %s assigned states: %s. New state: %s / Last state %s",
            self.name,
            self.assigned_states,
            new_state,
            last_state,
        )

        return self.turn_on()

    def async_turn_on(self, **kwargs: Any) -> None:
        _LOGGER.warning("Turn on %s", kwargs)
        super().async_turn_on(kwargs)

    def async_turn_off(self, **kwargs: Any) -> None:
        _LOGGER.warning("Turn off %s", kwargs)
        super().async_turn_on(kwargs)

    ####  Light Handling
    def turn_on(self) -> None:
        """Turn on the light group."""
        if not self.is_control_enabled():
            self.logger("%s: No control enabled", self.name)
            return False

        if self.is_on:
            self.logger("%s: Already on", self.name)
            return False

        if self.category is None or self.dim_level == 0:
            self.logger("%s: No category or dim is 0", self.name)
            return self.turn_off()

        self.last_update_from_entity = True
        service_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_BRIGHTNESS: int(self.dim_level * 255 / 100),
        }
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def turn_off(self) -> None:
        """Turn off the light group."""
        if not self.is_control_enabled():
            return False

        if not self.is_on:
            return False

        self.last_update_from_entity = True
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        # await self.async_turn_off()
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    #### Control Release

    def is_control_enabled(self) -> bool:
        entity_id = f"{SWITCH_DOMAIN}.area_light_control_{self.area.slug}"

        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_ON

    def _is_controlled_by_this_entity(self) -> bool:
        entity_id = (
            f"{SWITCH_DOMAIN}.area_manual_override_active_kitchen{self.area.slug}"
        )
        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_OFF

    def _set_controlled_by_this_entity(self, enabled: bool) -> None:
        if self.hass:
            entity_id = f"{SWITCH_DOMAIN}.area_manual_override_active_{self.area.slug}"
            service_data = {
                ATTR_ENTITY_ID: entity_id,
            }
            if enabled:
                self.hass.services.call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_OFF,
                    service_data,
                    blocking=False,
                    context=self._context,
                )
            else:
                self.hass.services.call(
                    SWITCH_DOMAIN,
                    SERVICE_TURN_ON,
                    service_data,
                    blocking=False,
                    context=self._context,
                )

    def _reset_control(self) -> None:
        self._set_controlled_by_this_entity(True)
        self.schedule_update_ha_state()
        self.logger.debug("{self.name}: Control Reset.")

    def _handle_group_state_change_primary(self) -> None:
        self.schedule_update_ha_state()

    def _handle_group_state_change_secondary(self) -> None:
        # If we changed last, unset
        if self.last_update_from_entity:
            self.logger.debug("%s: Group controlled by us", self.name)
            self.schedule_update_ha_state()
            # Don't do anything else in here.
        else:
            self._set_controlled_by_this_entity(False)
            # If not, it was manually controlled, stop controlling
            self.logger.debug("%s: Group controlled by something else.", self.name)
            # Reset to non-occupied if occupied, so if the room is entered again
            # we control again.
            # Start a timer to reset back to normal state.

    def _group_state_changed(self, event: Event[EventStateChangedData]) -> None:
        # If area is not occupied, ignore
        if not self.area.is_occupied():
            self._reset_control()
        else:
            origin_event = event.context.origin_event

            if not self.category:
                self._handle_group_state_change_primary()
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

                self._handle_group_state_change_secondary()

        # Update attribute
        self._attributes["last_update_from_entity"] = self.last_update_from_entity
        self.schedule_update_ha_state()

        return True
