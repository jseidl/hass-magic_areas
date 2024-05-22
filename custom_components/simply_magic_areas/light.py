"""Light controls for magic areas."""

import logging

from homeassistant.components.light import ATTR_BRIGHTNESS, DOMAIN as LIGHT_DOMAIN
from homeassistant.components.select import DOMAIN as SELECT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
)
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.event import async_track_state_change_event, call_later

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicLightGroup
from .base.magic import MagicArea
from .const import CONF_MANUAL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT, DOMAIN

_LOGGER = logging.getLogger(__name__)
DEPENDENCIES = ["magic_areas"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, _add_lights)


def _cleanup_entities(
    hass: HomeAssistant, new_ids: list[str], old_ids: list[str]
) -> None:
    entity_registry = async_get_er(hass)
    for ent_id in old_ids:
        if ent_id in new_ids:
            continue
        _LOGGER.warning("Deleting old entity %s", ent_id)
        entity_registry.async_remove(ent_id)


def _add_lights(area: MagicArea, async_add_entities: AddEntitiesCallback):
    existing_light_entities: list[str] = []
    if DOMAIN + LIGHT_DOMAIN in area.entities:
        _LOGGER.warning("Froggy %s", area.entities[DOMAIN + LIGHT_DOMAIN])
        existing_light_entities = [
            e["entity_id"] for e in area.entities[DOMAIN + LIGHT_DOMAIN]
        ]
    # Check if there are any lights
    if not area.has_entities(LIGHT_DOMAIN):
        _LOGGER.debug("No %s entities for area %s ", LIGHT_DOMAIN, area.name)
        _cleanup_entities(area.hass, [], existing_light_entities)
        return

    light_groups = []

    # Create light groups
    light_entities = [e["entity_id"] for e in area.entities[LIGHT_DOMAIN]]
    if area.is_meta():
        light_groups.append(MagicLightGroup(area, light_entities))
    else:
        # Create the ones with no entity automatically plus ones with an entity set
        light_group_object = AreaLightGroup(area, light_entities)
        light_groups.append(light_group_object)

    # Create all groups
    async_add_entities(light_groups)
    group_ids = [e.entity_id for e in light_groups]
    _cleanup_entities(area.hass, group_ids, existing_light_entities)


class AreaLightGroup(MagicLightGroup):
    """The light group to control the area lights specifically.

    One of these will be created for each type of light group, occupied,
    bright, sleep, accent, ...
    """

    def __init__(self, area: MagicArea, entities: list[str]) -> None:
        """Init the light group for the area."""
        MagicLightGroup.__init__(self, area, entities)

        category_title: str = "Simple Magic Areas Light"
        self._name: str = f"{category_title} ({self.area.name})"
        self._manual_timeout_cb: CALLBACK_TYPE | None = None
        self._icon: str = "mdi:ceiling-light"
        self._luminance_sensors: list[str] = []

        self._set_controlled_by_this_entity(True)

        # Add static attributes
        self.last_update_from_entity: bool = False
        self._attributes["lights"] = self._entity_ids
        self._attributes["last_update_from_entity"] = False

        self.logger.debug(
            "Light group %s %s created with entities: %s",
            self.name,
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
            self._attr_is_on = False

        self._load_illuminance_sensors()
        self.schedule_update_ha_state()

        # Setup state change listeners
        await self._setup_listeners()

        await super().async_added_to_hass()

    async def _setup_listeners(self, _=None) -> None:
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self.entity_id],
                self._update_group_state,
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [f"{SELECT_DOMAIN}.area_magic_{self.area.slug}"],
                self._area_state_change,
            )
        )

    def _load_illuminance_sensors(self) -> None:
        if SensorDeviceClass.ILLUMINANCE not in self.area.enties:
            return
        for component, entities in self.area.entities[SensorDeviceClass.ILLUMINANCE]:
            for entity in entities:
                if not entity:
                    continue

                if component == SENSOR_DOMAIN:
                    if ATTR_DEVICE_CLASS not in entity:
                        continue

                self._illuminance_sensors.append(entity[ATTR_ENTITY_ID])

    ### State Change Handling
    def _area_state_change(self, event: Event[EventStateChangedData]) -> None:
        if event.event_type != "state_changed":
            return
        if event.data["old_state"] is None or event.data["new_state"] is None:
            return
        automatic_control = self._is_control_enabled()

        if not automatic_control:
            self.logger.debug(
                "%s: Automatic control for light group is disabled, skipping", self.name
            )
            return False

        from_state = event.data["old_state"].state
        to_state = event.data["new_state"].state

        self.logger.debug(
            "Light group %s. New state: %s / Last state %s",
            self.name,
            to_state,
            from_state,
        )

        if self.area.has_configured_state(to_state):
            conf = self.area.state_config(to_state)
            self.turn_on(conf)
        else:
            self.logger.warning("%s: Unknown state %s", self.name, to_state)

    def _update_group_state(self, event: Event[EventStateChangedData]) -> None:
        if not self.area.is_occupied():
            self._reset_control()
        else:
            origin_event = event.context.origin_event
            if origin_event.event_type == "state_changed":
                # Skip non ON/OFF state changes
                if origin_event.data["old_state"].state not in [
                    STATE_ON,
                    STATE_OFF,
                ]:
                    return
                if origin_event.data["new_state"].state not in [
                    STATE_ON,
                    STATE_OFF,
                ]:
                    return
                if (
                    "restored" in origin_event.data["old_state"].attributes
                    and origin_event.data["old_state"].attributes["restored"]
                ):
                    return
                if self.last_update_from_entity:
                    self.last_update_from_entity = False
                    return
                self._set_controlled_by_this_entity(False)
                manual_timeout = self.area.config.get(
                    CONF_MANUAL_TIMEOUT, DEFAULT_MANUAL_TIMEOUT
                )
                if self._manual_timeout_cb is not None:
                    self._manual_timeout_cb()
                self._manual_timeout_cb = call_later(
                    self.hass, manual_timeout, self._reset_manual_timeout
                )

    def _reset_manual_timeout(self):
        self._set_controlled_by_this_entity(True)
        self._manual_timeout_cb = None

    ####  Light Handling
    def turn_on(self, conf: ConfigEntry) -> None:
        """Turn on the light group."""

        if not self._is_control_enabled():
            self.logger.debug("%s: No control enabled", self.name)
            return False

        self._entity_ids = conf.lights
        self.async_update_group_state()
        self.logger.debug(
            "Update light group %s %s %s %s %s",
            self.is_on,
            self.brightness,
            self.area.entities.keys(),
            conf.lights,
            self.area.entities[LIGHT_DOMAIN],
        )
        if conf.dim_level == 0:
            _LOGGER.debug("%s: Dim is 0", self.name)
            return self.turn_off()

        brightness = int(conf.dim_level * 255 / 100)
        if self.is_on and self.brightness == brightness:
            self.logger.debug("%s: Already on at %s", self.name, brightness)
            return False

        self.logger.debug("Turning on lights")
        self.last_update_from_entity = True
        service_data = {
            ATTR_ENTITY_ID: self.entity_id,
            ATTR_BRIGHTNESS: int(conf.dim_level * 255 / 100),
        }
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_ON, service_data)

        return True

    def turn_off(self) -> None:
        """Turn off the light group."""
        if not self._is_control_enabled():
            return False

        if not self.is_on:
            _LOGGER.debug("%s: Light already off", self.name)
            return False

        self.last_update_from_entity = True
        service_data = {ATTR_ENTITY_ID: self.entity_id}
        # await self.async_turn_off()
        self.hass.services.call(LIGHT_DOMAIN, SERVICE_TURN_OFF, service_data)

        return True

    #### Control Release
    def _is_control_enabled(self) -> bool:
        entity_id = f"{SWITCH_DOMAIN}.area_magic_light_control_{self.area.slug}"

        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_ON

    def _is_controlled_by_this_entity(self) -> bool:
        entity_id = (
            f"{SWITCH_DOMAIN}.area_magic_manual_override_active_kitchen{self.area.slug}"
        )
        switch_entity = self.hass.states.get(entity_id)

        return switch_entity.state.lower() == STATE_OFF

    def _set_controlled_by_this_entity(self, enabled: bool) -> None:
        if self.hass:
            entity_id = (
                f"{SWITCH_DOMAIN}.area_magic_manual_override_active_{self.area.slug}"
            )
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
