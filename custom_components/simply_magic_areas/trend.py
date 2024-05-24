"""Sensor controls for magic areas."""

import logging

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.trend.binary_sensor import SensorTrend
from homeassistant.components.trend.const import DOMAIN as TREND_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er

from .add_entities_when_ready import add_entities_when_ready
from .base.magic import MagicArea
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the magic area sensor config entry."""

    add_entities_when_ready(hass, async_add_entities, config_entry, add_trend)


def add_trend(area: MagicArea, async_add_entities: AddEntitiesCallback):
    """Add the sensors for the magic areas."""
    return
    existing_trend_entities: list[str] = []
    if DOMAIN + TREND_DOMAIN in area.entities:
        _LOGGER.warning("Froggy %s", area.entities[DOMAIN + TREND_DOMAIN])
        existing_trend_entities = [
            e["entity_id"] for e in area.entities[DOMAIN + TREND_DOMAIN]
        ]

    # Create the illuminance sensor if there are any illuminance sensors in the area.
    if not area.has_entities(SENSOR_DOMAIN):
        _cleanup_trend_entities(area.hass, [], existing_trend_entities)
        return

    aggregates = []

    # Check SENSOR_DOMAIN entities, count by device_class
    if not area.has_entities(SENSOR_DOMAIN):
        _cleanup_trend_entities(area.hass, [], existing_trend_entities)
        return

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
        _cleanup_trend_entities([], existing_trend_entities)
        return

    aggregates.append(HumdityTrendSensor(area=area, increasing=True))
    aggregates.append(HumdityTrendSensor(area=area, increasing=False))

    _cleanup_trend_entities(area.hass, aggregates, existing_trend_entities)

    async_add_entities(aggregates)


def _cleanup_trend_entities(
    hass: HomeAssistant, new_ids: list[str], old_ids: list[str]
) -> None:
    entity_registry = async_get_er(hass)
    for ent_id in old_ids:
        if ent_id in new_ids:
            continue
        _LOGGER.warning("Deleting old entity %s", ent_id)
        entity_registry.async_remove(ent_id)


class HumdityTrendSensor(SensorTrend):
    """Sensor for the magic area, tracking the humidity changes."""

    def __init__(self, area: MagicArea, increasing: bool) -> None:
        """Initialize an area trend group sensor."""

        super().__init__(
            name=f"Magic areas humidity occupancy ({area.name})"
            if increasing
            else f"Magic areas humidity empty ({area.name})",
            sample_duration=600 if increasing else 300,
            max_samples=3 if increasing else 2,
            min_gradient=0.01666 if increasing else -0.016666,
        )
