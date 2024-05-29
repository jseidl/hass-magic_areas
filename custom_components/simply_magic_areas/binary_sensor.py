"""Binary sensor control for magic areas."""

from datetime import UTC, datetime
import logging
import math

import numpy as np

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.event import async_track_state_change_event

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    AGGREGATE_MODE_ALL,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    DISTRESS_SENSOR_CLASSES,
    DATA_AREA_OBJECT,
    DOMAIN,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    area: MagicArea = hass.data[MODULE_DATA][config_entry.entry_id][DATA_AREA_OBJECT]

    entities = []
    existing_trend_entities = []
    if DOMAIN + BINARY_SENSOR_DOMAIN in area.entities:
        existing_trend_entities = [
            e["entity_id"] for e in area.entities[DOMAIN + BINARY_SENSOR_DOMAIN]
        ]
    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        entities.extend(create_aggregate_sensors(area, async_add_entities))

    if area.has_feature(CONF_FEATURE_HEALTH):
        entities.extend(create_health_sensors(area, async_add_entities))
    entities.extend(create_trend_sensors(area, async_add_entities))

    _cleanup_binary_sensor_entities(area.hass, entities, existing_trend_entities)


def create_health_sensors(
    area: MagicArea, async_add_entities: AddEntitiesCallback
) -> list[Entity]:
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[Entity] = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES, 0
    ):
        return []

    _LOGGER.debug("Creating health sensor for area (%s)", area.slug)
    entities = [AreaSensorGroupBinarySensor(area, entity_ids=distress_entities)]
    async_add_entities(entities)
    return entities


def create_aggregate_sensors(
    area: MagicArea, async_add_entities: AddEntitiesCallback
) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return []

    aggregates: list[Entity] = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    device_class_entities: dict[str, list[str]] = {}

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in device_class_entities:
            device_class_entities[entity[ATTR_DEVICE_CLASS]] = [entity["entity_id"]]
        else:
            device_class_entities[entity[ATTR_DEVICE_CLASS]].append(entity["entity_id"])

    for device_class, entity_count in device_class_entities.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES, 0
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            entity_count,
            area.slug,
        )
        aggregates.append(
            AreaSensorGroupBinarySensor(area, device_class, device_class_entities)
        )

    async_add_entities(aggregates)
    return aggregates


def create_trend_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the sensors for the magic areas."""

    # Create the illuminance sensor if there are any illuminance sensors in the area.
    if not area.has_entities(SENSOR_DOMAIN):
        return []

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return []

    found = False
    for entity in area.entities[SENSOR_DOMAIN]:
        if "device_class" not in entity:
            _LOGGER.debug(
                "Entity %s does not have device_class defined",
                entity["entity_id"],
            )
            continue

        if "unit_of_measurement" not in entity:
            _LOGGER.debug(
                "Entity %s does not have unit_of_measurement defined",
                entity["entity_id"],
            )
            continue

        # Dictionary of sensors by device class.
        device_class = entity["device_class"]
        if device_class != SensorDeviceClass.HUMIDITY:
            continue
        found = True

    if not found:
        return []

    aggregates.append(
        HumdityTrendSensor(
            area=area,
            increasing=True,
        )
    )
    aggregates.append(
        HumdityTrendSensor(
            area=area,
            increasing=False,
        )
    )

    async_add_entities(aggregates)

    return aggregates


def _cleanup_binary_sensor_entities(
    hass: HomeAssistant, new_ids: list[str], old_ids: list[str]
) -> None:
    entity_registry = async_get_er(hass)
    for ent_id in old_ids:
        if ent_id in new_ids:
            continue
        _LOGGER.warning("Deleting old entity %s", ent_id)
        entity_registry.async_remove(ent_id)


class AreaSensorGroupBinarySensor(MagicEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area: MagicArea,
        device_class: BinarySensorDeviceClass,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self, area=area, translation_key=device_class, domain=BINARY_SENSOR_DOMAIN
        )
        BinarySensorGroup.__init__(
            self,
            device_class=device_class,
            entity_ids=entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
        )

        self.area = area

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state:
            _LOGGER.debug(
                "%s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)
        await super().async_added_to_hass()
        self.async_write_ha_state()


class HumdityTrendSensor(MagicEntity, BinarySensorEntity):
    """Sensor for the magic area, tracking the humidity changes."""

    def __init__(self, area: MagicArea, increasing: bool) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self,
            area=area,
            translation_key="humidity_occupancy" if increasing else "humidity_empty",
            domain=BINARY_SENSOR_DOMAIN,
        )
        BinarySensorEntity.__init__(
            self,
        )
        self._attr_device_class = BinarySensorDeviceClass.MOISTURE
        self.area = area
        if increasing:
            self._sample_duration = 600
            self._max_samples = 3
            self._min_gradient = 0.01666
        else:
            self._sample_duration = 300
            self._max_samples = 2
            self._min_gradient = -0.016666
        self._invert = False
        self._min_samples = 2
        self._to_monitor = area.entity_unique_id(SENSOR_DOMAIN, "humidity")
        self._gradient = 0.0

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state:
            _LOGGER.debug(
                "%s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._to_monitor], self._trend_sensor_state_listener
            )
        )
        self.async_write_ha_state()

    @callback
    def _trend_sensor_state_listener(
        self,
        event: Event[EventStateChangedData],
    ) -> None:
        """Handle state changes on the observed device."""
        if (new_state := event.data["new_state"]) is None:
            return
        try:
            if self._attribute:
                state = new_state.attributes.get(self._attribute)
            else:
                state = new_state.state
            if state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                sample = (new_state.last_updated.timestamp(), float(state))  # type: ignore[arg-type]
                self.samples.append(sample)
                self.async_schedule_update_ha_state(True)
        except (ValueError, TypeError) as ex:
            _LOGGER.error(ex)

    async def async_update(self) -> None:
        """Get the latest data and update the states."""
        # Remove outdated samples
        if self._sample_duration > 0:
            cutoff = datetime.now(UTC).timestamp() - self._sample_duration
            while self.samples and self.samples[0][0] < cutoff:
                self.samples.popleft()

        if len(self.samples) < self._min_samples:
            return

        # Calculate gradient of linear trend
        await self.hass.async_add_executor_job(self._calculate_gradient)

        # Update state
        self._attr_is_on = (
            abs(self._gradient) > abs(self._min_gradient)
            and math.copysign(self._gradient, self._min_gradient) == self._gradient
        )

        if self._invert:
            self._attr_is_on = not self._attr_is_on

    def _calculate_gradient(self) -> None:
        """Compute the linear trend gradient of the current samples.

        This need run inside executor.
        """
        timestamps = np.array([t for t, _ in self.samples])
        values = np.array([s for _, s in self.samples])
        coeffs = np.polyfit(timestamps, values, 1)
        self._gradient = coeffs[0]

    def _update_state(self) -> None:
        self._attr_extra_state_attributes["gradient"] = self._gradient
        self._attr_extra_state_attributes["min_gradient"] = self.min_gradient
        self._attr_extra_state_attributes["entity_to_monitor"] = self._to_monitor
