DEPENDENCIES = ["magic_areas"]

import logging

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from .base import AggregateBase, SensorBase
from .const import (
    AGGREGATE_MODE_SUM,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    DATA_AREA_OBJECT,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

# async def async_setup_platform(
#     hass, config, async_add_entities, discovery_info=None
# ):  # pylint: disable=unused-argument

#     await load_sensors(hass, async_add_entities)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""
    # await async_setup_platform(hass, {}, async_add_entities)

    area_data = hass.data[MODULE_DATA][config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    await load_sensors(hass, async_add_entities, area)


async def load_sensors(hass, async_add_entities, area):

    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return

    device_class_count = {}

    for entity in area.entities[SENSOR_DOMAIN]:

        if "device_class" not in entity.keys():
            _LOGGER.warning(
                f"Entity {entity['entity_id']} does not have device_class defined"
            )
            continue

        if "unit_of_measurement" not in entity.keys():
            _LOGGER.warning(
                f"Entity {entity['entity_id']} does not have unit_of_measurement defined"
            )
            continue

        map_key = f"{entity['device_class']}/{entity['unit_of_measurement']}"
        if map_key not in device_class_count.keys():
            device_class_count[map_key] = 0

        device_class_count[map_key] += 1

    for map_key, entity_count in device_class_count.items():
        if entity_count < area.config.get(CONF_AGGREGATES_MIN_ENTITIES):
            continue

        device_class, unit_of_measurement = map_key.split("/")

        _LOGGER.debug(
            f"Creating aggregate sensor for device_class '{device_class}' ({unit_of_measurement}) with {entity_count} entities ({area.slug})"
        )
        aggregates.append(
            AreaSensorGroupSensor(hass, area, device_class, unit_of_measurement)
        )

    async_add_entities(aggregates)


class AreaSensorGroupSensor(AggregateBase, SensorBase):
    def __init__(self, hass, area, device_class, unit_of_measurement):

        """Initialize an area sensor group sensor."""

        self.area = area
        self.hass = hass
        self._mode = "sum" if device_class in AGGREGATE_MODE_SUM else "mean"
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        self._state = 0

        device_class_name = device_class.capitalize()
        self._name = (
            f"Area {device_class_name} [{unit_of_measurement}] ({self.area.name})"
        )

        self.tracking_listeners = []

    async def _initialize(self, _=None) -> None:

        _LOGGER.debug(f"{self.name} Sensor initializing.")

        self.load_sensors(SENSOR_DOMAIN, self._unit_of_measurement)

        # Setup the listeners
        await self._setup_listeners()

        _LOGGER.debug(f"{self.name} Sensor initialized.")
