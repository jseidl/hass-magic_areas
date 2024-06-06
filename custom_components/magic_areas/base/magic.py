"""Classes for Magic Areas and Meta Areas."""

from datetime import UTC, datetime
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_ON
from homeassistant.helpers.device_registry import async_get as devicereg_async_get
from homeassistant.helpers.entity_registry import (
    RegistryEntry,
    async_get as entityreg_async_get,
)
from homeassistant.util import slugify

from ..const import (
    AREA_STATE_OCCUPIED,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_INCLUDE_ENTITIES,
    CONF_TYPE,
    CONFIGURABLE_AREA_STATE_MAP,
    DATA_AREA_OBJECT,
    EVENT_MAGICAREAS_AREA_READY,
    EVENT_MAGICAREAS_READY,
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
    META_AREA_GLOBAL,
    MODULE_DATA,
    MetaAreaType,
)
from ..util import areas_loaded, flatten_entity_list, is_entity_list


class MagicArea:
    """Magic Area class.

    Tracks entities and updates area states and secondary states.
    """

    def __init__(
        self,
        hass,
        area,
        config,
        listen_event=EVENT_HOMEASSISTANT_STARTED,
        init_on_hass_running=True,
    ) -> None:
        """Initialize area."""
        self.logger = logging.getLogger(__name__)

        self.hass = hass
        self.name = area.name
        self.id = area.id
        self.icon = area.icon
        self.slug = slugify(self.name)
        self.hass_config = config
        self.initialized = False
        self.floor_id = area.floor_id
        self.is_meta_area = area.is_meta

        # Merged options
        area_config = dict(config.data)
        if config.options:
            area_config.update(config.options)
        self.config = area_config

        self.entities = {}
        self.magic_entities = {}

        self.last_changed = datetime.now(UTC)
        self.states = []

        self.loaded_platforms = []

        # Add callback for initialization
        if self.hass.is_running and init_on_hass_running:
            self.hass.async_create_task(self.initialize())
        else:
            self.hass.bus.async_listen_once(listen_event, self.initialize)

        self.logger.debug("%s: Primed for initialization.", self.name)

    def finalize_init(self):
        """Finalize initialization of the area."""
        self.initialized = True

        self.hass.bus.async_fire(EVENT_MAGICAREAS_AREA_READY, {"id": self.id})

        if not self.is_meta():
            # Check if we finished loading all areas
            if areas_loaded(self.hass):
                self.hass.bus.async_fire(EVENT_MAGICAREAS_READY)

        area_type = "Meta-Area" if self.is_meta() else "Area"
        self.logger.debug("%s (%s) initialized.", self.name, area_type)

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
            in self.config.get(CONF_EXCLUDE_ENTITIES)
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

            self.magic_entities[entity_domain].append(entity_id)

        self.logger.debug(
            "%s: Loaded magic entities: %s", self.name, str(self.magic_entities)
        )

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

                # Get latest state and create object
                latest_state = self.hass.states.get(entity_id)
                updated_entity = {"entity_id": entity_id}

                if latest_state:
                    # Need to exclude entity_id if present but latest_state.attributes
                    # is a ReadOnlyDict so we can't remove it, need to iterate and select
                    # all keys that are NOT entity_id
                    for attr_key, attr_value in latest_state.attributes.items():
                        if attr_key != "entity_id":
                            updated_entity[attr_key] = attr_value

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

    def __init__(self, hass, area, config) -> None:
        """Initialize Meta Area."""
        super().__init__(
            hass,
            area,
            config,
            EVENT_MAGICAREAS_READY,
            init_on_hass_running=areas_loaded(hass),
        )

    def areas_loaded(self, hass=None):
        """Check if all areas have finished loading."""
        hass_object = hass if hass else self.hass

        if MODULE_DATA not in hass_object.data:
            return False

        data = hass_object.data[MODULE_DATA]
        for area_info in data.values():
            area = area_info[DATA_AREA_OBJECT]
            if area.config.get(CONF_TYPE) != AREA_TYPE_META:
                if not area.initialized:
                    return False

        return True

    def get_active_areas(self):
        """Return areas that are occupied."""
        areas = self.get_child_areas()
        active_areas = []

        for area in areas:
            try:
                entity_id = f"binary_sensor.area_{area}"
                entity = self.hass.states.get(entity_id)

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
        areas = []

        for area_info in data.values():
            area = area_info[DATA_AREA_OBJECT]

            if area.is_meta_area:
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
            return False

        # Meta-areas need to wait until other magic areas are loaded.
        if not self.areas_loaded():
            self.logger.warning(
                "%s: Non-meta areas not loaded. This shouldn't happen.", self.name
            )
            return False

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

            for entities in area.entities.values():
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
