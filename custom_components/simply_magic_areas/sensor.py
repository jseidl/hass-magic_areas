"""Sensor controls for magic areas."""

from enum import StrEnum
import logging

from homeassistant.components.sensor import (
    DEVICE_CLASS_UNITS,
    DOMAIN as SENSOR_DOMAIN,
    UNIT_CONVERTERS,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.magic import MagicArea
from .base.primitives import SensorGroupBase
from .const import (
    AGGREGATE_MODE_SUM,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the magic area sensor config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the sensors for the magic areas."""
    # Create the illuminance sensor if there are any illuminance sensors in the area.
    if not area.has_entities(SENSOR_DOMAIN):
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return

    entities_by_device_class: dict[str, list] = {}

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
        if device_class not in entities_by_device_class:
            entities_by_device_class[device_class] = []
        entities_by_device_class[device_class].append(entity)

    # Create aggregates/illuminance sensor or illuminance ones.
    for item in entities_by_device_class.items():
        device_class = item[0]
        entities = item[1]

        if device_class != SensorDeviceClass.ILLUMINANCE:
            if not area.has_feature(CONF_FEATURE_AGGREGATION):
                continue
            if len(entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
                CONF_AGGREGATES_MIN_ENTITIES
            ):
                continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %d entities (%s)",
            device_class,
            len(entities),
            area.slug,
        )
        aggregates.append(AreaSensorGroupSensor(area=area, device_class=device_class))

    async_add_entities(aggregates)


class AreaSensorGroupSensor(SensorGroupBase):
    """Sensor for the magic area, group sensor with all the stuff in it."""

    def __init__(self, area: MagicArea, device_class: StrEnum) -> None:
        """Initialize an area sensor group sensor."""

        super().__init__(area=area, device_class=device_class)

        self._mode = "sum" if device_class in AGGREGATE_MODE_SUM else "mean"
        if device_class in UNIT_CONVERTERS:
            self._unit_of_measurement = UNIT_CONVERTERS[device_class].NORMALALIZED_UNIT
        else:
            self._unit_of_measurement = list(DEVICE_CLASS_UNITS[device_class])[0]

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = f"Simple Magic Areas {device_class_name} ({self.area.name})"

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing", self.name)

        self.load_sensors(SENSOR_DOMAIN, self._unit_of_measurement)

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug("%s Sensor initialized.", self.name)
