"""Platform file for Magic Areas threhsold sensors."""

import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.threshold.binary_sensor import ThresholdSensor
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_FEATURE_AGGREGATION,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_MIN_ENTITIES,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
)

_LOGGER = logging.getLogger(__name__)


def create_illuminance_threshold(area: MagicArea, hass: HomeAssistant) -> Entity:
    """Create threhsold light binary sensor based off illuminance aggregate."""

    if not area.has_feature(CONF_FEATURE_AGGREGATION):
        return None

    illuminance_threshold = area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_ILLUMINANCE_THRESHOLD, DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD
    )

    if illuminance_threshold == 0:
        return None

    if SensorDeviceClass.ILLUMINANCE not in area.feature_config(
        CONF_FEATURE_AGGREGATION
    ).get(
        CONF_AGGREGATES_SENSOR_DEVICE_CLASSES, DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES
    ):
        return None

    if SENSOR_DOMAIN not in area.entities:
        return None

    illuminance_sensors = [
        sensor
        for sensor in area.entities[SENSOR_DOMAIN]
        if ATTR_DEVICE_CLASS in sensor
        and sensor[ATTR_DEVICE_CLASS] == SensorDeviceClass.ILLUMINANCE
    ]

    if len(illuminance_sensors) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES, DEFAULT_AGGREGATES_MIN_ENTITIES
    ):
        return None

    illuminance_aggregate_entity_id = f"{SENSOR_DOMAIN}.area_illuminance_{area.slug}"
    threshold_sensor_name = f"Area Light (Calculated) ({area.name})"

    threshold_sensor = AreaThresholdSensor(
        area,
        hass=hass,
        device_class=BinarySensorDeviceClass.LIGHT,
        entity_id=illuminance_aggregate_entity_id,
        upper=illuminance_threshold,
        name=threshold_sensor_name,
    )

    return threshold_sensor


class AreaThresholdSensor(MagicEntity, ThresholdSensor):
    """Threshold sensor based off aggregates."""

    def __init__(
        self,
        area: MagicArea,
        hass: HomeAssistant,
        device_class: BinarySensorDeviceClass,
        entity_id: str,
        name: str,
        upper: int | None = None,
        lower: int | None = None,
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(self, area)
        ThresholdSensor.__init__(
            self,
            hass=hass,
            entity_id=entity_id,
            name=name,
            lower=lower,
            upper=upper,
            hysteresis=0,
            device_class=device_class,
            unique_id=slugify(name),
        )
