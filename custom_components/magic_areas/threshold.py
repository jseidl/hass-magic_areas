"""Platform file for Magic Areas threhsold sensors."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.threshold.binary_sensor import ThresholdSensor
from homeassistant.const import ATTR_DEVICE_CLASS
from homeassistant.helpers.entity import Entity

from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_FEATURE_AGGREGATION,
    DEFAULT_AGGREGATES_ILLUMINANCE_THRESHOLD,
    DEFAULT_AGGREGATES_SENSOR_DEVICE_CLASSES,
    MagicAreasFeatureInfoThrehsold,
)

_LOGGER = logging.getLogger(__name__)


def create_illuminance_threshold(area: MagicArea) -> Entity:
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

    if not illuminance_sensors:
        return None

    illuminance_aggregate_entity_id = (
        f"{SENSOR_DOMAIN}.magic_areas_aggregates_{area.slug}_aggregate_illuminance"
    )

    threshold_sensor = AreaThresholdSensor(
        area,
        device_class=BinarySensorDeviceClass.LIGHT,
        entity_id=illuminance_aggregate_entity_id,
        upper=illuminance_threshold,
    )

    return threshold_sensor


class AreaThresholdSensor(MagicEntity, ThresholdSensor):
    """Threshold sensor based off aggregates."""

    feature_info = MagicAreasFeatureInfoThrehsold()

    def __init__(
        self,
        area: MagicArea,
        device_class: BinarySensorDeviceClass,
        entity_id: str,
        upper: int | None = None,
        lower: int | None = None,
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self, area, domain=BINARY_SENSOR_DOMAIN, translation_key=device_class
        )
        ThresholdSensor.__init__(
            self,
            entity_id=entity_id,
            name=None,
            unique_id=self.unique_id,
            lower=lower,
            upper=upper,
            hysteresis=0,
            device_class=device_class,
        )
        delattr(self, "_attr_name")
