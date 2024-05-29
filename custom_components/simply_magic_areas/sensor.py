"""Sensor controls for magic areas."""

from enum import StrEnum
import logging

from homeassistant.components.group.sensor import (
    ATTR_MEAN,
    ATTR_SUM,
    SensorGroup,
    SensorStateClass,
)
from homeassistant.components.sensor import (
    DEVICE_CLASS_UNITS,
    DOMAIN as SENSOR_DOMAIN,
    UNIT_CONVERTERS,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.util import slugify

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    AGGREGATE_MODE_SUM,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ALWAYS_DEVICE_CLASS = {SensorDeviceClass.HUMIDITY, SensorDeviceClass.ILLUMINANCE}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the magic area sensor config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the sensors for the magic areas."""
    existing_sensor_entities: list[str] = []
    if DOMAIN + SENSOR_DOMAIN in area.entities:
        existing_sensor_entities = [
            e["entity_id"] for e in area.entities[DOMAIN + SENSOR_DOMAIN]
        ]

    # Create the illuminance sensor if there are any illuminance sensors in the area.
    if not area.has_entities(SENSOR_DOMAIN):
        _cleanup_sensor_entities(area.hass, [], existing_sensor_entities)
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        _cleanup_sensor_entities(area.hass, [], existing_sensor_entities)
        return

    entities_by_device_class: dict[str, list[str]] = {}

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
        entities_by_device_class[device_class].append(entity["entity_id"])

    # Create aggregates/illuminance sensor or illuminance ones.
    for item in entities_by_device_class.items():
        device_class = item[0]
        entities = item[1]

        if device_class not in ALWAYS_DEVICE_CLASS:
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
        aggregates.append(
            AreaSensorGroupSensor(
                area=area,
                device_class=device_class,
                entity_ids=entities,
            )
        )

    _cleanup_sensor_entities(area.hass, aggregates, existing_sensor_entities)

    async_add_entities(aggregates)


def _cleanup_sensor_entities(
    hass: HomeAssistant, new_ids: list[str], old_ids: list[str]
) -> None:
    entity_registry = async_get_er(hass)
    for ent_id in old_ids:
        if ent_id in new_ids:
            continue
        _LOGGER.warning("Deleting old entity %s", ent_id)
        entity_registry.async_remove(ent_id)


class AreaSensorGroupSensor(MagicEntity, SensorGroup):
    """Sensor for the magic area, group sensor with all the stuff in it."""

    def __init__(
        self,
        area: MagicArea,
        device_class: SensorDeviceClass,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group sensor."""

        MagicEntity.__init__(
            self, area=area, domain=SENSOR_DOMAIN, translation_key=device_class
        )
        SensorGroup.__init__(
            self,
            hass=area.hass,
            device_class=device_class,
            entity_ids=entity_ids,
            ignore_non_numeric=True,
            sensor_type=ATTR_SUM if device_class in AGGREGATE_MODE_SUM else ATTR_MEAN,
            state_class=SensorStateClass.TOTAL
            if device_class in AGGREGATE_MODE_SUM
            else SensorStateClass.MEASUREMENT,
            name=f"Simply Magic Areas {" ".join(device_class.split("_")).title()} ({self.area.name})",
            unique_id=slugify(
                f"Simply Magic Areas {" ".join(device_class.split("_")).title()} ({self.area.name})"
            ),
            unit_of_measurement=UNIT_CONVERTERS[device_class].NORMALALIZED_UNIT
            if device_class in UNIT_CONVERTERS
            else list(DEVICE_CLASS_UNITS[device_class])[0],
        )
