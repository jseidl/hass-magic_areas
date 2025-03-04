"""Wasp in a box binary sensor component."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import Event, EventStateChangedData, callback
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    CONF_WASP_IN_A_BOX_DELAY,
    CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
    WASP_IN_A_BOX_BOX_DEVICE_CLASSES,
    MagicAreasFeatureInfoWaspInABox,
    MagicAreasFeatures,
)

_LOGGER = logging.getLogger(__name__)


ATTR_BOX = "box"
ATTR_WASP = "wasp"


class AreaWaspInABoxBinarySensor(MagicEntity, BinarySensorEntity):
    """Wasp In The Box logic tracking sensor for the area."""

    feature_info = MagicAreasFeatureInfoWaspInABox()
    _wasp_sensors: list[str]
    _box_sensors: list[str]
    delay: int
    wasp: bool

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        self.delay = self.area.feature_config(MagicAreasFeatures.WASP_IN_A_BOX).get(
            CONF_WASP_IN_A_BOX_DELAY, DEFAULT_WASP_IN_A_BOX_DELAY
        )

        self._attr_device_class = BinarySensorDeviceClass.PRESENCE
        self._attr_extra_state_attributes = {
            ATTR_BOX: STATE_OFF,
            ATTR_WASP: STATE_OFF,
        }

        self.wasp = False
        self._attr_is_on: bool = False

        self._wasp_sensors = []
        self._box_sensors = []

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()

        # Check entities exist
        wasp_device_classes = self.area.feature_config(
            MagicAreasFeatures.WASP_IN_A_BOX
        ).get(
            CONF_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
            DEFAULT_WASP_IN_A_BOX_WASP_DEVICE_CLASSES,
        )

        for device_class in wasp_device_classes:
            dc_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{self.area.slug}_aggregate_{device_class}"
            dc_state = self.hass.states.get(dc_entity_id)
            if not dc_state:
                continue
            self._wasp_sensors.append(dc_entity_id)

        if not self._wasp_sensors:
            raise RuntimeError(f"{self.area.name}: No valid wasp sensors defined.")

        for device_class in WASP_IN_A_BOX_BOX_DEVICE_CLASSES:
            dc_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{self.area.slug}_aggregate_{device_class}"
            dc_state = self.hass.states.get(dc_entity_id)
            if not dc_state:
                continue
            self._box_sensors.append(dc_entity_id)

        if not self._box_sensors:
            raise RuntimeError(f"{self.area.name}: No valid wasp sensors defined.")

        # Add listeners

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._wasp_sensors, self._wasp_sensor_state_change
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._box_sensors, self._box_sensor_state_change
            )
        )

    def _wasp_sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Register wasp sensor state change event."""

        # Ignore state reports that aren't really a state change
        if not event.data["new_state"] or not event.data["old_state"]:
            return
        if event.data["new_state"].state == event.data["old_state"].state:
            return

        self.wasp_in_a_box(wasp_state=event.data["new_state"].state)

    def _box_sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Register box sensor state change event."""

        # Ignore state reports that aren't really a state change
        if not event.data["new_state"] or not event.data["old_state"]:
            return
        if event.data["new_state"].state == event.data["old_state"].state:
            return

        if self.delay:
            self.wasp = False
            self._attr_is_on = self.wasp
            self._attr_extra_state_attributes[ATTR_BOX] = event.data["new_state"].state
            self._attr_extra_state_attributes[ATTR_WASP] = STATE_OFF
            self.schedule_update_ha_state()
            self.hass.loop.call_soon_threadsafe(
                self.wasp_in_a_box_delayed,
                None,
                event.data["new_state"].state,
            )
        else:
            self.wasp_in_a_box(box_state=event.data["new_state"].state)

    @callback
    def wasp_in_a_box_delayed(
        self,
        wasp_state: str | None = None,
        box_state: str | None = None,
    ) -> None:
        """Call Wasp In A Box Logic function after a delay."""
        self.hass.loop.call_later(self.delay, self.wasp_in_a_box, wasp_state, box_state)

    def wasp_in_a_box(
        self,
        wasp_state: str | None = None,
        box_state: str | None = None,
    ) -> None:
        """Perform Wasp In A Box Logic."""

        if not wasp_state:
            # Get Wasp State
            wasp_state = STATE_OFF
            for wasp_sensor in self._wasp_sensors:
                wasp_sensor_state = self.hass.states.get(wasp_sensor)
                if not wasp_sensor_state:
                    continue
                if wasp_sensor_state.state == STATE_ON:
                    wasp_state = STATE_ON
                    break

        if not box_state:
            # Get Box State
            box_state = STATE_OFF
            for box_sensor in self._box_sensors:
                box_sensor_state = self.hass.states.get(box_sensor)
                if not box_sensor_state:
                    continue
                if box_sensor_state.state == STATE_ON:
                    box_state = STATE_ON
                    break

        # Main Logic
        if wasp_state == STATE_ON:
            self.wasp = True
        elif box_state == STATE_ON:
            self.wasp = False

        self._attr_extra_state_attributes[ATTR_BOX] = box_state
        self._attr_extra_state_attributes[ATTR_WASP] = wasp_state

        self._attr_is_on = self.wasp
        self.schedule_update_ha_state()
