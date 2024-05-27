"""Binary sensor control for magic areas."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.trend.binary_sensor import SensorTrend
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.util import slugify

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.magic import MagicArea
from .const import (
    AGGREGATE_MODE_ALL,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_HEALTH,
    DISTRESS_SENSOR_CLASSES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_sensors)


def add_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback) -> None:
    """Add the basic sensors for the area."""
    entities = []
    existing_trend_entities = []
    if DOMAIN + BINARY_SENSOR_DOMAIN in area.entities:
        _LOGGER.warning("Froggy %s", area.entities[DOMAIN + BINARY_SENSOR_DOMAIN])
        existing_trend_entities = [
            e["entity_id"] for e in area.entities[DOMAIN + BINARY_SENSOR_DOMAIN]
        ]
    # Create extra sensors
    if area.has_feature(CONF_FEATURE_AGGREGATION):
        entities.extend(create_aggregate_sensors(area, async_add_entities))

    if area.has_feature(CONF_FEATURE_HEALTH):
        entities.extend(create_health_sensors(area, async_add_entities))
    entities.extend(create_trend_sensors(area, async_add_entities))

    _cleanup_binary_sensor_entities(area.hass, entities, existing_trend_entities)


def create_health_sensors(
    area: MagicArea, async_add_entities: AddEntitiesCallback
) -> list[Entity]:
    """Add the health sensors for the area."""
    if not area.has_feature(CONF_FEATURE_HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[Entity] = []

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in DISTRESS_SENSOR_CLASSES:
            continue

        distress_entities.append(entity)

    if len(distress_entities) < area.feature_config(CONF_FEATURE_AGGREGATION).get(
        CONF_AGGREGATES_MIN_ENTITIES, 0
    ):
        return []

    _LOGGER.debug("Creating health sensor for area (%s)", area.slug)
    entities = [AreaSensorGroupBinarySensor(area, entity_ids=distress_entities)]
    async_add_entities(entities)
    return entities


def create_aggregate_sensors(
    area: MagicArea, async_add_entities: AddEntitiesCallback
) -> list[Entity]:
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
            device_class_entities[entity[ATTR_DEVICE_CLASS]] = [entity["entity_id"]]
        else:
            device_class_entities[entity[ATTR_DEVICE_CLASS]].append(entity["entity_id"])

    for device_class, entity_count in device_class_entities.items():
        if entity_count < area.feature_config(CONF_FEATURE_AGGREGATION).get(
            CONF_AGGREGATES_MIN_ENTITIES, 0
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            entity_count,
            area.slug,
        )
        aggregates.append(
            AreaSensorGroupBinarySensor(area, device_class, device_class_entities)
        )

    async_add_entities(aggregates)
    return aggregates


def create_trend_sensors(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the sensors for the magic areas."""

    # Create the illuminance sensor if there are any illuminance sensors in the area.
    if not area.has_entities(SENSOR_DOMAIN):
        return []

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        return []

    found = False
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
        if device_class != SensorDeviceClass.HUMIDITY:
            continue
        found = True

    if not found:
        return []

    aggregates.append(
        HumdityTrendSensor(
            area=area,
            increasing=True,
        )
    )
    aggregates.append(
        HumdityTrendSensor(
            area=area,
            increasing=False,
        )
    )

    async_add_entities(aggregates)

    return aggregates


def _cleanup_binary_sensor_entities(
    hass: HomeAssistant, new_ids: list[str], old_ids: list[str]
) -> None:
    entity_registry = async_get_er(hass)
    for ent_id in old_ids:
        if ent_id in new_ids:
            continue
        _LOGGER.warning("Deleting old entity %s", ent_id)
        entity_registry.async_remove(ent_id)


class AreaSensorGroupBinarySensor(MagicEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area: MagicArea,
        device_class: BinarySensorDeviceClass,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(self, area)
        BinarySensorGroup.__init__(
            self,
            device_class=device_class,
            entity_ids=entity_ids,
            mode=device_class in AGGREGATE_MODE_ALL,
            name=f"Area {" ".join(device_class.split("_")).title()} ({self.area.name})",
        )

        self.area = area

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state:
            _LOGGER.debug(
                "%s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._state = last_state.state == STATE_ON
        await super().async_added_to_hass()
        self.async_write_ha_state()


class HumdityTrendSensor(MagicEntity, SensorTrend):
    """Sensor for the magic area, tracking the humidity changes."""

    def __init__(self, area: MagicArea, increasing: bool) -> None:
        """Initialize an area trend group sensor."""

        MagicEntity.__init__(self, area)
        SensorTrend.__init__(
            self,
            name=f"Simply Magic Areas humidity occupancy ({area.name})"
            if increasing
            else f"Simply Magic Areas humidity empty ({area.name})",
            sample_duration=600 if increasing else 300,
            max_samples=3 if increasing else 2,
            min_gradient=0.01666 if increasing else -0.016666,
            invert=False,
            min_samples=2,
            attribute=None,
            entity_id=f"{SENSOR_DOMAIN}.simply_magic_areas_humidity_{area.slug}",
        )
        self._state = False

    async def async_added_to_hass(self) -> None:
        """Call when entity about to be added to hass."""
        last_state = await self.async_get_last_state()
        if last_state:
            _LOGGER.debug(
                "%s restored [state=%s]",
                self.name,
                last_state.state,
            )
            self._state = last_state.state == STATE_ON

        await super().async_added_to_hass()
        await self.async_update()
        self.async_write_ha_state()
