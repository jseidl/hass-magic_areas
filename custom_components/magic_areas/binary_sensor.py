"""Binary sensor control for magic areas."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .base.presence import AreaStateBinarySensor
from .const import (
    AGGREGATE_MODE_ALL,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    DEFAULT_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES,
    MagicAreasFeatureInfoAggregates,
    MagicAreasFeatureInfoHealth,
)
from .threshold import create_illuminance_threshold
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback) -> None:
    """Add the basic sensors for the area."""
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

    # Add all entities
    async_add_entities(entities)

    # Cleanup
    if BINARY_SENSOR_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities, area.magic_entities[BINARY_SENSOR_DOMAIN]
        )


def create_health_sensors(area: MagicArea) -> list[Entity]:
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[Entity] = []

    health_sensor_device_classes = area.feature_config(CONF_FEATURE_HEALTH).get(
        CONF_HEALTH_SENSOR_DEVICE_CLASSES, DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES
    )

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in health_sensor_device_classes:
            continue

        distress_entities.append(entity["entity_id"])

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
            self, area, domain=BINARY_SENSOR_DOMAIN, translation_key=device_class
        )
        BinarySensorGroup.__init__(
            self,
            device_class=device_class,
            name=None,
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
