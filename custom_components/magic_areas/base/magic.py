"""Classes for Magic Areas and Meta Areas."""

from collections.abc import Iterable
from datetime import UTC, datetime
import logging

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import (
    RegistryEntry,
    async_get as entityreg_async_get,
)
from homeassistant.util import slugify

from custom_components.magic_areas.const import (
    AREA_STATE_OCCUPIED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_INCLUDE_ENTITIES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_TYPE,
    CONFIGURABLE_AREA_STATE_MAP,
    DATA_AREA_OBJECT,
    DEFAULT_PRESENCE_DEVICE_PLATFORMS,
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
    META_AREA_GLOBAL,
    MODULE_DATA,
    MetaAreaType,
)

# Helpers


def is_entity_list(item):
    """Check if item is a list."""
    basestring = (str, bytes)
    return isinstance(item, Iterable) and not isinstance(item, basestring)


def flatten_entity_list(input_list):
    """Recursively flatten a nested list into a flat list."""
    for i in input_list:
        if is_entity_list(i):
            yield from flatten_entity_list(i)
        else:
            yield i


# Classes


class BasicArea:
    """An interchangeable area object for Magic Areas to consume."""

    id: str
    name: str
    icon: str | None = None
    floor_id: str | None = None
    is_meta: bool = False


class MagicArea:
    """Magic Area class.

    Tracks entities and updates area states and secondary states.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        area: BasicArea,
        config: ConfigEntry,
    ) -> None:
        """Initialize the magic area with all the stuff."""
        self.hass: HomeAssistant = hass
        self.name: str = area.name
        # Default to the icon for the area.
        self.icon: str = area.icon or "mdi:room"
        self.id: str = area.id
        self.slug: str = slugify(self.name)
        self.hass_config: ConfigEntry = config
        self.initialized: bool = False
        self.floor_id: str | None = area.floor_id
        self.logger = logging.getLogger(__name__)

        # Merged options
        area_config = dict(config.data)
        if config.options:
            area_config.update(config.options)
        self.config = area_config

        self.entities: dict[str, list[dict[str, str]]] = {}
        self.magic_entities: dict[str, list[dict[str, str]]] = {}

        self.last_changed: int = datetime.now(UTC)  # type: ignore  # noqa: PGH003

        self.states = []

        self.loaded_platforms: list[str] = []

        self.logger.debug("%s: Primed for initialization.", self.name)

    def finalize_init(self):
        """Finalize initialization of the area."""
        self.initialized = True
        self.logger.debug(
            "%s (%s) initialized.", self.name, "Meta-Area" if self.is_meta() else "Area"
        )

    def is_occupied(self) -> bool:
        """Return if area is occupied."""
        return self.has_state(AREA_STATE_OCCUPIED)

    def has_state(self, state) -> bool:
        """Check if area has a given state."""
        return state in self.states

    def has_configured_state(self, state) -> bool:
        """Check if area supports a given state."""
        state_opts = CONFIGURABLE_AREA_STATE_MAP.get(state, None)

        if not state_opts:
            return False

        state_entity, state_value = state_opts

        if state_entity and state_value:
            return True

        return False

    def has_feature(self, feature) -> bool:
        """Check if area has a given feature."""
        enabled_features = self.config.get(CONF_ENABLED_FEATURES)

        # Deal with legacy
        if isinstance(enabled_features, list):
            return feature in enabled_features

        # Handle everything else
        if not isinstance(enabled_features, dict):
            self.logger.warning(
                "%s: Invalid configuration for %s", self.name, CONF_ENABLED_FEATURES
            )
            return False

        return feature in enabled_features

    def feature_config(self, feature) -> dict:
        """Return configuration for a given feature."""
        if not self.has_feature(feature):
            self.logger.debug("%s: Feature '%s' not enabled.", self.name, feature)
            return {}

        options = self.config.get(CONF_ENABLED_FEATURES, {})

        if not options:
            self.logger.debug("%s: No feature config found for %s", self.name, feature)

        return options.get(feature, {})

    def available_platforms(self):
        """Return available platforms to area type."""
        available_platforms = []

        if not self.is_meta():
            available_platforms = MAGIC_AREAS_COMPONENTS
        else:
            available_platforms = (
                MAGIC_AREAS_COMPONENTS_GLOBAL
                if self.id == META_AREA_GLOBAL.lower()
                else MAGIC_AREAS_COMPONENTS_META
            )

        return available_platforms

    @property
    def area_type(self):
        """Return the area type."""
        return self.config.get(CONF_TYPE)

    def is_meta(self) -> bool:
        """Return if area is Meta or not."""
        return self.area_type == AREA_TYPE_META

    def is_interior(self):
        """Return if area type is interior or not."""
        return self.area_type == AREA_TYPE_INTERIOR

    def is_exterior(self):
        """Return if area type is exterior or not."""
        return self.area_type == AREA_TYPE_EXTERIOR

    def _is_magic_area_entity(self, entity: RegistryEntry) -> bool:
        """Return if entity belongs to this integration instance."""
        return entity.config_entry_id == self.hass_config.entry_id

    def _should_exclude_entity(self, entity: RegistryEntry) -> bool:
        """Exclude entity."""
        return (
            entity.config_entry_id == self.hass_config.entry_id  # Is magic_area entity
            or entity.disabled  # Is disabled
            or entity.entity_id  # In excluded list
            in self.config.get(CONF_EXCLUDE_ENTITIES, [])
        )

    async def load_entities(self) -> None:
        """Load entities into entity list."""

        entity_list = []
        include_entities = self.config.get(CONF_INCLUDE_ENTITIES)

        entity_registry = entityreg_async_get(self.hass)
        device_registry = devicereg_async_get(self.hass)

        # Add entities from devices in this area
        devices_in_area = device_registry.devices.get_devices_for_area_id(self.id)
        for device in devices_in_area:
            entity_list.extend(
                [
                    entity.entity_id
                    for entity in entity_registry.entities.get_entries_for_device_id(
                        device.id
                    )
                    if not self._should_exclude_entity(entity)
                ]
            )

        # Add entities that are specifically set as this area but device is not or has no device.
        entities_in_area = entity_registry.entities.get_entries_for_area_id(self.id)
        entity_list.extend(
            [
                entity.entity_id
                for entity in entities_in_area
                if entity.entity_id not in entity_list
                and not self._should_exclude_entity(entity)
            ]
        )

        if include_entities and isinstance(include_entities, list):
            entity_list.extend(include_entities)

        self.load_entity_list(entity_list)

        self.logger.debug(
            "%s: Found area entities: %s",
            self.name,
            str(self.entities),
        )

    def load_magic_entities(self):
        """Load magic areas-generated entities."""

        entity_registry = entityreg_async_get(self.hass)

        # Add magic are entities
        entities_for_config_id = (
            entity_registry.entities.get_entries_for_config_entry_id(
                self.hass_config.entry_id
            )
        )

        for entity_id in [entity.entity_id for entity in entities_for_config_id]:
            entity_domain = entity_id.split(".")[0]

            if entity_domain not in self.magic_entities:
                self.magic_entities[entity_domain] = []

            self.magic_entities[entity_domain].append(self.get_entity_dict(entity_id))

        self.logger.debug(
            "%s: Loaded magic entities: %s", self.name, str(self.magic_entities)
        )

    def get_entity_dict(self, entity_id) -> dict[str, str]:
        """Return entity_id in a dictionary with attributes (if available)."""

        # Get latest state and create object
        latest_state = self.hass.states.get(entity_id)
        entity_dict = {"entity_id": entity_id}

        if latest_state:
            # Need to exclude entity_id if present but latest_state.attributes
            # is a ReadOnlyDict so we can't remove it, need to iterate and select
            # all keys that are NOT entity_id
            for attr_key, attr_value in latest_state.attributes.items():
                if attr_key != "entity_id":
                    entity_dict[attr_key] = attr_value

        return entity_dict

    def load_entity_list(self, entity_list):
        """Populate entity list with loaded entities."""
        self.logger.debug("%s: Original entity list: %s", self.name, str(entity_list))

        flattened_entity_list = flatten_entity_list(entity_list)
        unique_entities = set(flattened_entity_list)

        self.logger.debug("%s: Unique entities: %s", self.name, str(unique_entities))

        for entity_id in unique_entities:
            self.logger.debug("%s: Loading entity: %s", self.name, entity_id)

            try:
                # pylint: disable-next=unused-variable
                entity_component, entity_name = entity_id.split(".")

                updated_entity = self.get_entity_dict(entity_id)

                # Ignore groups
                if is_entity_list(updated_entity["entity_id"]):
                    self.logger.debug(
                        "%s: '%s' is probably a group, skipping...",
                        self.name,
                        entity_id,
                    )
                    continue

                if entity_component not in self.entities:
                    self.entities[entity_component] = []

                self.entities[entity_component].append(updated_entity)

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as err:
                self.logger.error(
                    "%s: Unable to load entity '%s': %s", self.name, entity_id, str(err)
                )

        # Load our own entities
        self.load_magic_entities()

    def get_presence_sensors(self) -> list[str]:
        """Return list of entities used for presence tracking."""

        sensors: list[str] = []

        if self.is_meta():
            # MetaAreas track their children
            child_areas = self.get_child_areas()  # pylint: disable=no-member
            for child_area in child_areas:
                entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{child_area}_area_state"
                sensors.append(entity_id)
            return sensors

        valid_presence_platforms = self.config.get(
            CONF_PRESENCE_DEVICE_PLATFORMS, DEFAULT_PRESENCE_DEVICE_PLATFORMS
        )

        for component, entities in self.entities.items():
            if component not in valid_presence_platforms:
                continue

            for entity in entities:
                if not entity:
                    continue

                if component == BINARY_SENSOR_DOMAIN:
                    if ATTR_DEVICE_CLASS not in entity:
                        continue

                    if entity[ATTR_DEVICE_CLASS] not in self.config.get(
                        CONF_PRESENCE_SENSOR_DEVICE_CLASS, []
                    ):
                        continue

                sensors.append(entity[ATTR_ENTITY_ID])

        # Append presence_hold switch as a presence_sensor
        if self.has_feature(CONF_FEATURE_PRESENCE_HOLD):
            presence_hold_switch_id = (
                f"{SWITCH_DOMAIN}.magic_areas_presence_hold_{self.slug}"
            )
            sensors.append(presence_hold_switch_id)

        return sensors

    async def initialize(self, _=None) -> None:
        """Initialize area."""
        self.logger.debug("%s: Initializing area...", self.name)

        await self.load_entities()

        self.finalize_init()

    def has_entities(self, domain):
        """Check if area has entities."""
        return domain in self.entities


class MagicMetaArea(MagicArea):
    """Magic Meta Area class."""

    def get_active_areas(self):
        """Return areas that are occupied."""
        areas = self.get_child_areas()
        active_areas = []

        for area in areas:
            try:
                entity_id = f"binary_sensor.area_{area}"
                entity = self.hass.states.get(entity_id)

                if not entity:
                    self.logger.debug("%s: Unable to get area state entity.", area)
                    continue

                if entity.state == STATE_ON:
                    active_areas.append(area)

            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                self.logger.error(
                    "%s: Unable to get active area state: %s", area, str(e)
                )

        return active_areas

    def get_child_areas(self):
        """Return areas that a Meta area is watching."""
        data = self.hass.data[MODULE_DATA]
        areas: list[str] = []

        for area_info in data.values():
            area: MagicArea = area_info[DATA_AREA_OBJECT]

            if area.is_meta():
                continue

            if self.floor_id:
                if self.floor_id == area.floor_id:
                    areas.append(area.slug)
            else:
                if (
                    self.id == MetaAreaType.GLOBAL
                    or area.config.get(CONF_TYPE) == self.id
                ):
                    areas.append(area.slug)

        return areas

    async def initialize(self, _=None) -> None:
        """Initialize Meta area."""
        if self.initialized:
            self.logger.warning("%s: Already initialized, ignoring.", self.name)
            return None

        self.logger.debug("%s: Initializing meta area...", self.name)

        await self.load_entities()

        self.finalize_init()

    async def load_entities(self) -> None:
        """Load entities into entity list."""
        entity_list = []
        child_areas = self.get_child_areas()

        data = self.hass.data[MODULE_DATA]
        for area_info in data.values():
            area = area_info[DATA_AREA_OBJECT]

            if area.slug not in child_areas:
                continue

            for entities in area.magic_entities.values():
                for entity in entities:
                    if not isinstance(entity["entity_id"], str):
                        self.logger.debug(
                            "%s: Entity ID is not a string: '%s' (probably a group, skipping)",
                            self.name,
                            str(entity["entity_id"]),
                        )
                        continue

                    # Skip excluded entities
                    if entity["entity_id"] in self.config.get(CONF_EXCLUDE_ENTITIES):
                        continue

                    entity_list.append(entity["entity_id"])

        self.load_entity_list(entity_list)

        self.logger.debug(
            "%s: Loaded entities for meta area: %s", self.name, str(self.entities)
        )
