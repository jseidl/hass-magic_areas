"""Wasp in a box binary sensor component."""

from datetime import UTC, datetime
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
    CONF_WASP_IN_A_BOX_DEVICE_CLASSES,
    DEFAULT_WASP_IN_A_BOX_DELAY,
    DEFAULT_WASP_IN_A_BOX_DEVICE_CLASSES,
    MagicAreasFeatureInfoWaspInABox,
    MagicAreasFeatures,
)

_LOGGER = logging.getLogger(__name__)


ATTR_BOX = "box"
ATTR_WASP = "wasp"


class AreaWaspInABoxBinarySensor(MagicEntity, BinarySensorEntity):
    """Wasp In The Box logic tracking sensor for the area."""

    feature_info = MagicAreasFeatureInfoWaspInABox()
    _wasp_sensors: list[str] = []
    _box_sensor: str
    delay: int = 0
    wasp: bool = False

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        device_classes = self.area.feature_config(MagicAreasFeatures.WASP_IN_A_BOX).get(
            CONF_WASP_IN_A_BOX_DEVICE_CLASSES, DEFAULT_WASP_IN_A_BOX_DEVICE_CLASSES
        )

        for device_class in device_classes:
            dc_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{area.slug}_aggregate_{device_class}"
            self._wasp_sensors.append(dc_entity_id)

        if not self._wasp_sensors:
            raise RuntimeError(f"{self.area.name}: No valid wasp sensors defined.")

        self._box_sensor = (
            f"{BINARY_SENSOR_DOMAIN}.magic_areas_aggregates_{area.slug}_aggregate_door"
        )

        self.delay = self.area.feature_config(MagicAreasFeatures.WASP_IN_A_BOX).get(
            CONF_WASP_IN_A_BOX_DELAY, DEFAULT_WASP_IN_A_BOX_DELAY
        )

        self._attr_device_class = BinarySensorDeviceClass.PRESENCE
        self._attr_extra_state_attributes = {
            ATTR_BOX: STATE_OFF,
            ATTR_WASP: STATE_OFF,
        }
        self._attr_is_on: bool = False

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug("%s: Wasp In A Box sensor initialized", self.area.name)

    async def _setup_listeners(self) -> None:
        """Attach state chagne listeners."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._wasp_sensors, self._wasp_sensor_state_change
            )
        )
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._box_sensor], self._box_sensor_state_change
            )
        )

    def _wasp_sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Register wasp sensor state change event."""

        # Ignore state reports taht aren't really a state change
        if (
            event.data["old_state"]
            and event.data["new_state"]
            and event.data["new_state"].state == event.data["old_state"].state
        ):
            return

        self.wasp_in_a_box(wasp_state=event.data["new_state"].state)

    def _box_sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Register box sensor state change event."""

        # Ignore state reports taht aren't really a state change
        if (
            event.data["old_state"]
            and event.data["new_state"]
            and event.data["new_state"].state == event.data["old_state"].state
        ):
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
                datetime.now(UTC),
            )
        else:
            self.wasp_in_a_box(box_state=event.data["new_state"].state)

    @callback
    def wasp_in_a_box_delayed(
        self,
        *,
        wasp_state: str | None = None,
        box_state: str | None = None,
        extra: datetime | None = None,
    ) -> None:
        """Call Wasp In A Box Logic function after a delay."""
        self.hass.loop.call_later(
            self.delay, self.wasp_in_a_box, wasp_state, box_state, extra
        )

    def wasp_in_a_box(
        self,
        *,
        wasp_state: str | None = None,
        box_state: str | None = None,
        extra: datetime | None = None,
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
            box_sensor_state = self.hass.states.get(self._box_sensor)
            if not box_sensor_state:
                _LOGGER.warning(
                    "%s: Could not get state for box sensor %s.",
                    self.area.name,
                    self._box_sensor,
                )
                return

            box_state = box_sensor_state.state

        # Main Logic
        if wasp_state == STATE_ON:
            self.wasp = True
        elif box_state == STATE_ON:
            self.wasp = False

        self._attr_extra_state_attributes[ATTR_BOX] = box_state
        self._attr_extra_state_attributes[ATTR_WASP] = wasp_state

        self._attr_is_on = self.wasp
        self.schedule_update_ha_state()
