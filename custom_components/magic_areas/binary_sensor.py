"""Binary sensor control for magic areas."""

from datetime import UTC, datetime
import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from custom_components.magic_areas.base.entities import MagicEntity
from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.base.presence import AreaStateBinarySensor
from custom_components.magic_areas.const import (
    AGGREGATE_MODE_ALL,
    ATTR_ACTIVE_SENSORS,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_BLE_TRACKER_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_BLE_TRACKERS,
    CONF_FEATURE_HEALTH,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
    EMPTY_STRING,
    MagicAreasFeatureInfoAggregates,
    MagicAreasFeatureInfoBLETrackers,
    MagicAreasFeatureInfoHealth,
)
from custom_components.magic_areas.helpers.area import get_area_from_config_entry
from custom_components.magic_areas.threshold import create_illuminance_threshold
from custom_components.magic_areas.util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)

# Classes


class AreaSensorGroupBinarySensor(MagicEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area: MagicArea,
        device_class: str,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self, area, domain=BINARY_SENSOR_DOMAIN, translation_key=device_class
        )
        BinarySensorGroup.__init__(
            self,
            device_class=(
                BinarySensorDeviceClass(device_class) if device_class else None
            ),
            name=EMPTY_STRING,
            unique_id=self._attr_unique_id,
            entity_ids=entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
        )
        delattr(self, "_attr_name")


class AreaAggregateBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoAggregates()


class AreaHealthBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoHealth()


class AreaBLETrackerBinarySensor(MagicEntity, BinarySensorEntity):
    """BLE Tracker monitoring sensor for the area."""

    feature_info = MagicAreasFeatureInfoBLETrackers()
    _sensors: list[str]

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        self._sensors = self.area.feature_config(CONF_FEATURE_BLE_TRACKERS).get(
            CONF_BLE_TRACKER_ENTITIES, []
        )

        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_extra_state_attributes = {
            ATTR_ENTITY_ID: self._sensors,
            ATTR_ACTIVE_SENSORS: [],
        }
        self._attr_is_on: bool = False

    async def _restore_state(self) -> None:
        """Restore the state of the BLE Tracker monitor sensor entity on initialize."""
        last_state = await self.async_get_last_state()

        if last_state is None:
            _LOGGER.debug("%s: New BLE Tracker monitor sensor created", self.area.name)
            self._attr_is_on = False
        else:
            _LOGGER.debug(
                "%s: BLE Tracker monitor sensor restored [state=%s]",
                self.area.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)

        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()
        await self._restore_state()

        # Setup the listeners
        await self._setup_listeners()

        self.hass.loop.call_soon_threadsafe(self._update_state, datetime.now(UTC))

        _LOGGER.debug("%s: BLE Tracker monitor sensor initialized", self.area.name)

    async def _setup_listeners(self) -> None:
        """Attach state chagne listeners."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._sensors, self._sensor_state_change
            )
        )

    def _sensor_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Call update state from track state change event."""

        self._update_state()

    @callback
    def _update_state(self, extra: datetime | None = None) -> None:
        """Calculate state based off BLE tracker sensors."""

        calculated_state: bool = False
        active_sensors: list[str] = []

        for sensor in self._sensors:
            sensor_state = self.hass.states.get(sensor)

            if not sensor_state:
                continue

            normalized_state = sensor_state.state.lower()

            if (
                normalized_state == self.area.slug
                or normalized_state == self.area.id
                or normalized_state == self.area.name.lower()
            ):
                calculated_state = True
                active_sensors.append(sensor)

        _LOGGER.debug(
            "%s: BLE Tracker monitor sensor state change: %s -> %s",
            self.area.name,
            self._attr_is_on,
            calculated_state,
        )

        self._attr_is_on = calculated_state
        self._attr_extra_state_attributes[ATTR_ACTIVE_SENSORS] = active_sensors
        self.schedule_update_ha_state()


# Setup


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the area binary sensor config entry."""

    area: MagicArea | None = get_area_from_config_entry(hass, config_entry)
    assert area is not None

    entities = []

    # Create main presence sensor
    entities.append(AreaStateBinarySensor(area))

    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        entities.extend(create_aggregate_sensors(area))
        illuminance_threshold_sensor = create_illuminance_threshold(area)
        if illuminance_threshold_sensor:
            entities.append(illuminance_threshold_sensor)

    if area.has_feature(CONF_FEATURE_HEALTH):
        entities.extend(create_health_sensors(area))

    if area.has_feature(CONF_FEATURE_BLE_TRACKERS):
        entities.extend(create_ble_tracker_sensor(area))

    # Add all entities
    async_add_entities(entities)

    # Cleanup
    if BINARY_SENSOR_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities, area.magic_entities[BINARY_SENSOR_DOMAIN]
        )


def create_ble_tracker_sensor(area: MagicArea) -> list[AreaBLETrackerBinarySensor]:
    """Add the BLE tracker sensor for the area."""
    if not area.has_feature(CONF_FEATURE_BLE_TRACKERS):
        return []

    if not area.feature_config(CONF_FEATURE_BLE_TRACKERS).get(
        CONF_BLE_TRACKER_ENTITIES, []
    ):
        return []

    return [
        AreaBLETrackerBinarySensor(
            area,
        )
    ]


def create_health_sensors(area: MagicArea) -> list[AreaHealthBinarySensor]:
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[str] = []

    health_sensor_device_classes = area.feature_config(CONF_FEATURE_HEALTH).get(
        CONF_HEALTH_SENSOR_DEVICE_CLASSES, DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES
    )

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in health_sensor_device_classes:
            continue

        distress_entities.append(entity[ATTR_ENTITY_ID])

    if not distress_entities:
        _LOGGER.debug(
            "%s: No binary sensor found for configured device classes: %s.",
            area.name,
            str(health_sensor_device_classes),
        )
        return []

    _LOGGER.debug(
        "%s: Creating health sensor with the following entities: %s",
        area.slug,
        str(distress_entities),
    )
    entities = [
        AreaHealthBinarySensor(
            area,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_ids=distress_entities,
        )
    ]

    return entities


def create_aggregate_sensors(area: MagicArea) -> list[Entity]:
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
            device_class_entities[entity[ATTR_DEVICE_CLASS]] = []

        device_class_entities[entity[ATTR_DEVICE_CLASS]].append(entity["entity_id"])

    for device_class, entity_list in device_class_entities.items():
        if len(entity_list) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES, 0
        ):
            continue

        if device_class not in area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            len(entity_list),
            area.slug,
        )
        aggregates.append(AreaAggregateBinarySensor(area, device_class, entity_list))

    return aggregates
