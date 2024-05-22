"""Binary sensor control for magic areas."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.magic import MagicArea
from .base.primitives import BinarySensorGroupBase
from .const import (
    AGGREGATE_MODE_ALL,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    DISTRESS_SENSOR_CLASSES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the basic sensors for the area."""
    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        create_aggregate_sensors(area, async_add_entities)

    if area.has_feature(CONF_FEATURE_HEALTH):
        create_health_sensors(area, async_add_entities)


def create_health_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return

    distress_entities = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES
    ):
        return

    _LOGGER.debug("Creating health sensor for area (%s)", area.slug)
    async_add_entities([AreaDistressBinarySensor(area)])


def create_aggregate_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Create the aggregate sensors for the area."""
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check BINARY_SENSOR_DOMAIN entities, count by device_class
    if BINARY_SENSOR_DOMAIN not in area.entities:
        return

    device_class_count = {}

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in device_class_count:
            device_class_count[entity[ATTR_DEVICE_CLASS]] = 0

        device_class_count[entity[ATTR_DEVICE_CLASS]] += 1

    for device_class, entity_count in device_class_count.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            entity_count,
            area.slug,
        )
        aggregates.append(AreaSensorGroupBinarySensor(area, device_class))

    async_add_entities(aggregates)


class AreaSensorGroupBinarySensor(BinarySensorGroupBase):
    """Group binary sensor for the area."""

    def __init__(self, area: MagicArea, device_class: BinarySensorDeviceClass) -> None:
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, device_class)

        self._mode = "all" if device_class in AGGREGATE_MODE_ALL else "single"

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = f"Area {device_class_name} ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing.", self.name)

        self.load_sensors(BINARY_SENSOR_DOMAIN)

        # Setup the listeners
        await self._setup_listeners()

        # Refresh state
        self._update_state()

        self.logger.debug("%s Sensor initialized.", self.name)


class AreaDistressBinarySensor(BinarySensorGroupBase):
    """The distress binary sensor for the area."""

    def __init__(self, area: MagicArea) -> None:
        """Initialize an area sensor group binary sensor."""

        super().__init__(area, BinarySensorDeviceClass.PROBLEM)

        self._name = f"Area Health ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing.", self.name)

        self.load_sensors()

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug("%s Sensor initialized.", self.name)

    def load_sensors(self) -> None:
        """Load the sensors from the system."""
        # Fetch sensors
        self.sensors = []

        for entity in self.area.entities[BINARY_SENSOR_DOMAIN]:
            if ATTR_DEVICE_CLASS not in entity:
                continue

            if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
                continue

            self.sensors.append(entity["entity_id"])

        self._attributes = {"sensors": self.sensors, "active_sensors": []}
