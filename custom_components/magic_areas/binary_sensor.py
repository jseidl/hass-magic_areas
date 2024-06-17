"""Binary sensor control for magic areas."""

import logging

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.group.binary_sensor import BinarySensorGroup
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .add_entities_when_ready import add_entities_when_ready
from .base.entities import MagicEntity
from .base.feature import (
    MagicAreasFeatureInfoAggregates,
    MagicAreasFeatureInfoHealth,
    MagicAreasFeatureInfoPresenceTracking,
)
from .base.magic import MagicArea
from .base.presence import AreaStateTracker
from .const import (
    AggregatesOptionKey,
    AreaHealthOptionKey,
    AreaInfoOptionKey,
    CustomAttribute,
    MagicAreasEvent,
    MagicAreasFeatures,
    MetaAreaIcons,
    MetaAreaType,
    OptionSetKey,
)
from .threshold import create_illuminance_threshold
from .util import cleanup_removed_entries

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Area config entry."""

    add_entities_when_ready(
        hass, async_add_entities, config_entry, add_sensors, with_hass=True
    )


def add_sensors(
    area: MagicArea, hass: HomeAssistant, async_add_entities: AddEntitiesCallback
) -> None:
    """Add the basic sensors for the area."""
    entities = []

    # Create main presence sensor
    entities.append(AreaStateBinarySensor(area))

    # Create extra sensors
    if area.config.has_feature(MagicAreasFeatures.AGGREGATES):
        entities.extend(create_aggregate_sensors(area))
        illuminance_threshold_sensor = create_illuminance_threshold(area, hass)
        if illuminance_threshold_sensor:
            entities.append(illuminance_threshold_sensor)

    if area.config.has_feature(MagicAreasFeatures.HEALTH):
        entities.extend(create_health_sensors(area))

    # Add all entities
    async_add_entities(entities)

    # Cleanup
    if BINARY_SENSOR_DOMAIN in area.magic_entities:
        cleanup_removed_entries(
            area.hass, entities, area.magic_entities[BINARY_SENSOR_DOMAIN]
        )


def create_health_sensors(area: MagicArea) -> list[Entity]:
    """Add the health sensors for the area."""
    if not area.config.has_feature(MagicAreasFeatures.HEALTH):
        return []

    if BINARY_SENSOR_DOMAIN not in area.entities:
        return []

    distress_entities: list[Entity] = []

    health_sensor_device_classes = (
        area.config.get(OptionSetKey.AREA_HEALTH)
        .get(AreaHealthOptionKey.DEVICE_CLASSES)
        .value()
    )

    for entity in area.entities[BINARY_SENSOR_DOMAIN]:
        if ATTR_DEVICE_CLASS not in entity:
            continue

        if entity[ATTR_DEVICE_CLASS] not in health_sensor_device_classes:
            continue

        distress_entities.append(entity["entity_id"])

    if not distress_entities:
        _LOGGER.debug(
            "%s: No binary sensor found for configured device classes: %s.",
            area.name,
            str(health_sensor_device_classes),
        )
        return []

    _LOGGER.debug(
        "%s: Creating health sensor with the following entities: %s",
        area.slug,
        str(distress_entities),
    )
    entities = [
        AreaHealthBinarySensor(
            area,
            device_class=BinarySensorDeviceClass.PROBLEM,
            entity_ids=distress_entities,
        )
    ]

    return entities


def create_aggregate_sensors(area: MagicArea) -> list[Entity]:
    """Create the aggregate sensors for the area."""
    # Create aggregates
    if not area.config.has_feature(MagicAreasFeatures.AGGREGATES):
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
            device_class_entities[entity[ATTR_DEVICE_CLASS]] = []

        device_class_entities[entity[ATTR_DEVICE_CLASS]].append(entity["entity_id"])

    for device_class, entity_list in device_class_entities.items():
        if (
            len(entity_list)
            < area.config(OptionSetKey.AGGREGATES)
            .get(AggregatesOptionKey.MIN_ENTITIES)
            .value()
        ):
            continue

        if (
            device_class
            not in area.config(OptionSetKey.AGGREGATES)
            .get(AggregatesOptionKey.BINARY_SENSOR_DEVICE_CLASSES)
            .value()
        ):
            continue

        _LOGGER.debug(
            "Creating aggregate sensor for device_class '%s' with %s entities (%s)",
            device_class,
            len(entity_list),
            area.slug,
        )
        aggregates.append(AreaAggregateBinarySensor(area, device_class, entity_list))

    return aggregates


class AreaSensorGroupBinarySensor(MagicEntity, BinarySensorGroup):
    """Group binary sensor for the area."""

    def __init__(
        self,
        area: MagicArea,
        device_class: BinarySensorDeviceClass,
        entity_ids: list[str],
    ) -> None:
        """Initialize an area sensor group binary sensor."""

        MagicEntity.__init__(
            self, area, domain=BINARY_SENSOR_DOMAIN, translation_key=device_class
        )
        BinarySensorGroup.__init__(
            self,
            device_class=device_class,
            name=None,
            unique_id=self._attr_unique_id,
            entity_ids=entity_ids,
            mode=device_class
            in area.config.get(OptionSetKey.AGGREGATES)
            .get(AggregatesOptionKey.MODE_ALL)
            .value(),
        )
        delattr(self, "_attr_name")


class AreaAggregateBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoAggregates()


class AreaHealthBinarySensor(AreaSensorGroupBinarySensor):
    """Aggregate sensor for the area."""

    feature_info = MagicAreasFeatureInfoHealth()


class AreaStateBinarySensor(MagicEntity, BinarySensorEntity):
    """Create an area presence presence sensor entity that tracks the current occupied state."""

    feature_info = MagicAreasFeatureInfoPresenceTracking()

    # Init & Teardown

    def __init__(self, area: MagicArea) -> None:
        """Initialize the area presence binary sensor."""

        MagicEntity.__init__(self, area, domain=BINARY_SENSOR_DOMAIN)
        BinarySensorEntity.__init__(self)

        # Load area state tracker
        self._state_tracker: AreaStateTracker | None = None

        self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        self._attr_extra_state_attributes = {}
        self._attr_is_on: bool = False

    async def async_added_to_hass(self) -> None:
        """Call to add the system to hass."""
        await super().async_added_to_hass()
        await self._restore_state()
        await self._load_attributes()

        # Setup the listeners
        await self._setup_listeners()

        if self._state_tracker:
            self._state_tracker.force_update()

        _LOGGER.debug("%s: area presence binary sensor initialized", self.area.name)

    async def _setup_listeners(self) -> None:

        # Setup state chagne listener
        self.hass.bus.async_listen(
            MagicAreasEvent.AREA_STATE_CHANGED, self._area_state_changed
        )

        # Setup area state tracker
        self._state_tracker = AreaStateTracker(self.hass, self.area)

        self.async_on_remove(self._destroy_tracker_callbacks)

    def _destroy_tracker_callbacks(self) -> None:
        """Destroy all callbacks from tracker."""
        for tracked in self._state_tracker.get_tracked_entities():
            self.hass.async_add_executor_job(tracked)

    async def _restore_state(self) -> None:
        """Restore the state of the presence sensor entity on initialize."""
        last_state = await self.async_get_last_state()

        if last_state is None:
            _LOGGER.debug("%s: New presence sensor created", self.area.name)
            self._attr_is_on = False
        else:
            _LOGGER.debug(
                "%s: presence sensor restored [state=%s]",
                self.area.name,
                last_state.state,
            )
            self._attr_is_on = last_state.state == STATE_ON
            self._attr_extra_state_attributes = dict(last_state.attributes)

        self.schedule_update_ha_state()

    # Binary sensor overrides

    @property
    def icon(self):
        """Return the icon to be used for this entity."""
        if self.area.is_meta():
            if self.area.id == MetaAreaType.EXTERIOR:
                return MetaAreaIcons.EXTERIOR
            if self.area.id == MetaAreaType.INTERIOR:
                return MetaAreaIcons.INTERIOR
            if self.area.id == MetaAreaType.GLOBAL:
                return MetaAreaIcons.GLOBAL

        return self.area.icon

    # Helpers

    async def _load_attributes(self) -> None:
        # Set attributes
        if self.area.is_meta():
            self._attr_extra_state_attributes.update(
                {
                    CustomAttribute.AREAS,
                }
            )

        # Add common attributes
        self._attr_extra_state_attributes.update(
            {
                CustomAttribute.STATES: [],
                CustomAttribute.ACTIVE_SENSORS: [],
                CustomAttribute.LAST_ACTIVE_SENSORS: [],
                CustomAttribute.PRESENCE_SENSORS: [],
                CustomAttribute.AREA_TYPE: self.area.config.get(OptionSetKey.AREA_INFO)
                .get(AreaInfoOptionKey.TYPE)
                .value(),
                CustomAttribute.CLEAR_TIMEOUT: 0,  # @FIXME get starting clear timeout from conf
            }
        )

    # Area change handlers
    def _area_state_changed(
        self, area_id: str, states_tuple: tuple[list[str], list[str]]
    ) -> None:
        """Handle area state change event."""

        # pylint: disable-next=unused-variable
        new_states, old_states = states_tuple

        if area_id != self.area.id:
            _LOGGER.debug(
                "%s: Area state change event not for us. Skipping. (req: %s}/self: %s)",
                self.area.name,
                area_id,
                self.area.id,
            )
            return

        _LOGGER.debug(
            "%s: Binary presence sensor detected area state change.", self.area.name
        )

        if self._state_tracker:
            self._attr_is_on = self.area.is_occupied()
            self._attr_extra_state_attributes.update(self._state_tracker.get_metadata())
            self.schedule_update_ha_state()
