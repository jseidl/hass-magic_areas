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
from homeassistant.util import slugify

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
)
from .threshold import create_illuminance_threshold

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(
        hass, async_add_entities, config_entry, add_sensors, with_hass=True
    )


def add_sensors(
    area: MagicArea, hass: HomeAssistant, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the basic sensors for the area."""
    entities = []

    # Create main presence sensor
    entities.append(AreaStateBinarySensor(area))

    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        entities.extend(create_aggregate_sensors(area))
        illuminance_threshold_sensor = create_illuminance_threshold(area, hass)
        if illuminance_threshold_sensor:
            entities.append(illuminance_threshold_sensor)

    if area.has_feature(CONF_FEATURE_HEALTH):
        entities.extend(create_health_sensors(area))

    # Add all entities
    async_add_entities(entities)


def create_health_sensors(area: MagicArea) -> list[Entity]:
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[Entity] = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in area.feature_config(
            CONF_FEATURE_HEALTH
        ).get(CONF_HEALTH_SENSOR_DEVICE_CLASSES, DEFAULT_HEALTH_SENSOR_DEVICE_CLASSES):
            continue

        distress_entities.append(entity["entity_id"])

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES, 0
    ):
        return []

    _LOGGER.debug("Creating health sensor for area (%s)", area.slug)
    entities = [
        AreaSensorGroupBinarySensor(
            area,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_ids=distress_entities,
            name=f"Area Health ({area.name})",
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
        aggregates.append(AreaSensorGroupBinarySensor(area, device_class, entity_list))

    return aggregates


class AreaSensorGroupBinarySensor(MagicEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area: MagicArea,
        device_class: BinarySensorDeviceClass,
        entity_ids: list[str],
        name: str | None = None,
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(self, area)

        if not name:
            device_class_name = " ".join(device_class.split("_")).title()
            name = f"Area {device_class_name} ({self.area.name})"

        BinarySensorGroup.__init__(
            self,
            device_class=device_class,
            entity_ids=entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
            name=name,
            unique_id=slugify(name),
        )
