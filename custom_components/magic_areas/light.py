"""Platform file for Magic Area's light entities."""

import logging

from homeassistant.components.group.light import LightGroup
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_SERVICE_DATA,
    EVENT_CALL_SERVICE,
    EVENT_STATE_CHANGED,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import Context, Event

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.feature import MagicAreasFeatureInfoLightGroups
from .const import (
    LIGHT_GROUP_CATEGORIES,
    LightGroupCategory,
    MagicAreasEvent,
    MagicAreasFeatures,
    OptionSetKey,
)
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_lights)


def add_lights(area, async_add_entities):
    """Add all the light entities for all features that have one."""
    # Check feature availability
    if not area.config.has_feature(MagicAreasFeatures.LIGHT_GROUPS):
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
            category_lights = (
                area.config.get(OptionSetKey.LIGHT_GROUPS).get(category).value()
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
                translation_key=LightGroupCategory.ALL,
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

    def __init__(self, area, entity_ids, translation_key: str | None = None):
        """Initialize parent class and state."""
        MagicEntity.__init__(
            self, area, domain=LIGHT_DOMAIN, translation_key=translation_key
        )
        LightGroup.__init__(
            self,
            name=None,
            unique_id=self.unique_id,
            entity_ids=entity_ids,
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
        data = {}

        # Copy parameters over
        for arg_keyword, arg_value in kwargs.items():
            data[arg_keyword] = arg_value

        # Active lights
        active_lights = self._get_active_lights()

        if active_lights:
            _LOGGER.debug(
                "%s: restricting call to active lights: %s",
                self.area.name,
                str(active_lights),
            )

        data[ATTR_ENTITY_ID] = active_lights if active_lights else self._entity_ids

        # Forward call
        await self.hass.services.async_call(
            LIGHT_DOMAIN,
            SERVICE_TURN_ON,
            data,
            blocking=True,
            context=Context(id=self.area.context_id),
        )


class AreaLightGroup(MagicLightGroup):
    """Magic Light Group."""

    async def async_added_to_hass(self) -> None:
        """Restore state and setup listeners."""
        # Get last state
        last_state = await self.async_get_last_state()

        if last_state:
            self.logger.debug(
                "%s: State restored [state=%s]", self.name, last_state.state
            )
            self._attr_is_on = last_state.state == STATE_ON
        else:
            self._attr_is_on = False

        self.schedule_update_ha_state()

        # Setup state change listeners
        await self._setup_listeners()

        await super().async_added_to_hass()

    async def _setup_listeners(self, _=None) -> None:
        """Set up listeners for area state chagne."""

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_CALL_SERVICE,
                self.turn_on_off_event_listener,
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_STATE_CHANGED,
                self.entity_state_changed_event_listener,
            )
        )
        self.async_on_remove(
            self.hass.bus.async_listen(
                MagicAreasEvent.AREA_STATE_CHANGED,
                self.area_state_changed_event_listener,
            )
        )

    async def area_state_changed_event_listener(self, event: Event) -> None:
        """Track Magic Areas' AREA_STATE_CHANGED events."""

        if event.data.get("area_id", None) != self.area.id:
            return

    async def turn_on_off_event_listener(self, event: Event) -> None:
        """Track 'light.turn_off' and 'light.turn_on' service calls."""

        # Ignore events for non-lights
        domain = event.data.get(ATTR_DOMAIN)
        if domain != LIGHT_DOMAIN:
            return

        service_data = event.data[ATTR_SERVICE_DATA]

        entity_ids = service_data.get(ATTR_ENTITY_ID, [])

        if not any(eid in self._entity_ids for eid in entity_ids):
            return

        if event.context.id != self.area.context_id:
            _LOGGER.debug(
                "%s: Detected external change on member light (service call): %s, releasing control.",
                self.area.name,
                entity_ids,
            )

    async def entity_state_changed_event_listener(self, event: Event) -> None:
        """Track 'state_changed' events."""

        entity_id = event.data.get(ATTR_ENTITY_ID, "")

        # Ignore state changes not from our entities
        if entity_id not in self._entity_ids:
            return

        new_state = event.data.get("new_state", None)

        if not new_state:
            return

        if new_state.context.id != self.area.context_id:
            _LOGGER.debug(
                "%s: Detected external change on member light (state change): %s, releasing control.",
                self.area.name,
                entity_id,
            )
