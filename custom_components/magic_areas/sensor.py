from enum import StrEnum
import logging

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.base.primitives import SensorGroupBase
from custom_components.magic_areas.const import (
    AGGREGATE_MODE_SUM,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
)
from custom_components.magic_areas.util import add_entities_when_ready

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    # Create aggregates
    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return

    device_class_uom_pairs = []

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
            "Creating aggregate sensor for device_class '%s' (%s) with %d entities (%s)",
            device_class,
            unit_of_measurement,
            entity_count,
            area.slug,
        )
        aggregates.append(
            AreaSensorGroupSensor(area, device_class, unit_of_measurement)
        )

    async_add_entities(aggregates)


class AreaSensorGroupSensor(SensorGroupBase):
    """Sensor for the magic area, group sensor with all the stuff in it."""

    def __init__(
        self, area: MagicArea, device_class: StrEnum, unit_of_measurement: str
    ) -> None:
        """Initialize an area sensor group sensor."""

        super().__init__(area, device_class)

        self._mode = "sum" if device_class in AGGREGATE_MODE_SUM else "mean"
        self._unit_of_measurement = unit_of_measurement

        device_class_name = " ".join(device_class.split("_")).title()
        self._name = (
            f"Area {device_class_name} [{unit_of_measurement}] ({self.area.name})"
        )

    async def _initialize(self, _=None) -> None:
        self.logger.debug("%s Sensor initializing", self.name)

        self.load_sensors(SENSOR_DOMAIN, self._unit_of_measurement)

        # Setup the listeners
        await self._setup_listeners()

        self.logger.debug("%s Sensor initialized.", self.name)
