"""Sensor controls for magic areas."""

from collections import Counter
import logging

from homeassistant.components.group.sensor import (
    ATTR_MEAN,
    ATTR_SUM,
    SensorGroup,
    SensorStateClass,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    AGGREGATE_MODE_SUM,
    AGGREGATE_MODE_TOTAL_SENSOR,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_FEATURE_AGGREGATION,
    DEFAULT_AGGREGATES_MIN_ENTITIES,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
    DEFAULT_SENSOR_PRECISION,
    MagicAreasFeatureInfoAggregates,
)
from .util import cleanup_removed_entries

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

    entities_to_add = []

    if area.has_feature(CONF_FEATURE_AGGREGATION):
        entities_to_add.extend(create_aggregate_sensors(area))

    if entities_to_add:
        async_add_entities(entities_to_add)

    if SENSOR_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities_to_add, area.magic_entities[SENSOR_DOMAIN]
        )


def create_aggregate_sensors(area: MagicArea) -> list[Entity]:
    """Create the aggregate sensors for the area."""

    eligible_entities: dict[str, str] = {}
    unit_of_measurement_map: dict[str, list[str]] = {}

    aggregates = []

    if SENSOR_DOMAIN not in area.entities:
        return []

    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return []

    for entity in area.entities[SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            _LOGGER.debug(
                "Entity %s does not have device_class defined",
                entity["entity_id"],
            )
            continue

        if ATTR_UNIT_OF_MEASUREMENT not in entity:
            _LOGGER.debug(
                "Entity %s does not have unit_of_measurement defined",
                entity["entity_id"],
            )
            continue

        # Dictionary of sensors by device class.
        device_class = entity[ATTR_DEVICE_CLASS]
        if device_class not in eligible_entities:
            eligible_entities[entity[ATTR_DEVICE_CLASS]] = []

        # Dictionary of seen unit of measurements by device class.
        if device_class not in unit_of_measurement_map:
            unit_of_measurement_map[device_class] = []

        unit_of_measurement_map[device_class].append(entity[ATTR_UNIT_OF_MEASUREMENT])
        eligible_entities[device_class].append(entity["entity_id"])

    # Create aggregates
    for device_class, entities in eligible_entities.items():

        if len(entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES
        ):
            continue

        if device_class not in area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
            DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %d entities (%s)",
            device_class,
            len(entities),
            area.slug,
        )

        # Infer most-popular unit of measurement
        unit_of_measurements = Counter(unit_of_measurement_map[device_class])
        most_common_unit_of_measurement = unit_of_measurements.most_common(1)[0][0]

        aggregates.append(
            AreaAggregateSensor(
                area=area,
                device_class=device_class,
                entity_ids=entities,
                unit_of_measurement=most_common_unit_of_measurement,
            )
        )

    return aggregates


class AreaSensorGroupSensor(MagicEntity, SensorGroup):
    """Sensor for the magic area, group sensor with all the stuff in it."""

    def __init__(
        self,
        area: MagicArea,
        device_class: SensorDeviceClass,
        entity_ids: list[str],
        unit_of_measurement: str,
    ) -> None:
        """Initialize an area sensor group sensor."""

        MagicEntity.__init__(
            self, area=area, domain=SENSOR_DOMAIN, translation_key=device_class
        )

        final_unit_of_measurement = None

        # Resolve unit of measurement
        unit_attr_name = f"{device_class}_unit"
        if hasattr(area.hass.config.units, unit_attr_name):
            final_unit_of_measurement = getattr(area.hass.config.units, unit_attr_name)
        else:
            final_unit_of_measurement = unit_of_measurement

        self._attr_suggested_display_precision = DEFAULT_SENSOR_PRECISION
        self.device_class = device_class

        SensorGroup.__init__(
            self,
            hass=area.hass,
            device_class=device_class,
            entity_ids=entity_ids,
            ignore_non_numeric=True,
            sensor_type=ATTR_SUM if device_class in AGGREGATE_MODE_SUM else ATTR_MEAN,
            state_class=(
                SensorStateClass.TOTAL
                if device_class in AGGREGATE_MODE_TOTAL_SENSOR
                else SensorStateClass.MEASUREMENT
            ),
            unit_of_measurement=final_unit_of_measurement,
            name=None,
            unique_id=self._attr_unique_id,
        )
        delattr(self, "_attr_name")


class AreaAggregateSensor(AreaSensorGroupSensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoAggregates()
