import logging

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from custom_components.magic_areas.base.primitives import SensorGroupBase
from custom_components.magic_areas.const import (
    AGGREGATE_MODE_SUM,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
)
from custom_components.magic_areas.util import add_entities_when_ready

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Demo config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)

def add_sensors(area, async_add_entities):
    
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return

    device_class_uom_pairs = []

    for entity in area.entities[SENSOR_DOMAIN]:
        if "device_class" not in entity.keys():
            _LOGGER.debug(
                f"Entity {entity['entity_id']} does not have device_class defined"
            )
            continue

        if "unit_of_measurement" not in entity.keys():
            _LOGGER.debug(
                f"Entity {entity['entity_id']} does not have unit_of_measurement defined"
            )
            continue

        dc_uom_pair = (entity["device_class"], entity["unit_of_measurement"])
        device_class_uom_pairs.append(dc_uom_pair)

    # Sort out individual pairs, if they show up more than CONF_AGGREGATES_MIN_ENTITIES,
    # we create a sensor for them
    unique_pairs = set(device_class_uom_pairs)

    for dc_uom_pair in unique_pairs:
        entity_count = device_class_uom_pairs.count(dc_uom_pair)

        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES
        ):
            continue

        device_class, unit_of_measurement = dc_uom_pair

        _LOGGER.debug(
            f"Creating aggregate sensor for device_class '{device_class}' ({unit_of_measurement}) with {entity_count} entities ({area.slug})"
        )
        aggregates.append(
            AreaSensorGroupSensor(area, device_class, unit_of_measurement)
        )

    async_add_entities(aggregates)

class AreaSensorGroupSensor(SensorGroupBase):
    def __init__(self, area, device_class, unit_of_measurement):
        """Initialize an area sensor group sensor."""

        super().__init__(area, device_class)

        self._mode = "sum" if device_class in AGGREGATE_MODE_SUM else "mean"
        self._unit_of_measurement = unit_of_measurement
        
        device_class_name = " ".join(device_class.split("_")).title()
        self._name = (
            f"Area {device_class_name} [{unit_of_measurement}] ({self.area.name})"
        )

    async def _initialize(self, _=None) -> None:
        self.logger.debug(f"{self.name} Sensor initializing.")

        self.load_sensors(SENSOR_DOMAIN, self._unit_of_measurement)

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug(f"{self.name} Sensor initialized.")
