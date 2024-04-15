"""Classes for Magic Areas and Meta Areas."""

from datetime import datetime, UTC
import logging

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_ON
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
    DOMAIN,
    EVENT_MAGICAREAS_AREA_READY,
    EVENT_MAGICAREAS_READY,
    MAGIC_AREAS_COMPONENTS,
    MAGIC_AREAS_COMPONENTS_GLOBAL,
    MAGIC_AREAS_COMPONENTS_META,
    MAGIC_DEVICE_ID_PREFIX,
    META_AREA_GLOBAL,
    MODULE_DATA,
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
        self.slug = slugify(self.name)
        self.hass_config = config
        self.initialized = False

        # Merged options
        area_config = dict(config.data)
        if config.options:
            area_config.update(config.options)
        self.config = area_config

        self.entities = {}

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

    def is_valid_entity(self, entity_object) -> bool:
        """Validate an entity."""
        # Ignore our own entities
        if entity_object.device_id:
            device_registry = self.hass.helpers.device_registry.async_get(self.hass)
            device_object = device_registry.async_get(entity_object.device_id)

            if device_object:
                our_device_tuple = (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.id}")

                if our_device_tuple in device_object.identifiers:
                    self.logger.debug(
                        "%s: Entity '%s' is ours, skipping.",
                        self.name,
                        entity_object.entity_id,
                    )
                    return False

        if entity_object.disabled:
            return False

        if entity_object.entity_id in self.config.get(CONF_EXCLUDE_ENTITIES):
            return False

        return True

    async def _is_entity_from_area(self, entity_object) -> bool:
        """Check if an entity is from a given area."""
        # Check entity's area_id
        if entity_object.area_id == self.id:
            return True

        # Check device's area id, if available
        if entity_object.device_id:
            device_registry = self.hass.helpers.device_registry.async_get(self.hass)
            if entity_object.device_id in device_registry.devices:
                device_object = device_registry.devices[entity_object.device_id]
                if device_object.area_id == self.id:
                    return True

        # Check if entity_id is in CONF_INCLUDE_ENTITIES
        if entity_object.entity_id in self.config.get(CONF_INCLUDE_ENTITIES):
            return True

        return False

    async def load_entities(self) -> None:
        """Load entities into entity list."""
        entity_list = []
        include_entities = self.config.get(CONF_INCLUDE_ENTITIES)

        entity_registry = self.hass.helpers.entity_registry.async_get(self.hass)

        for entity_object in entity_registry.entities.values():
            # Check entity validity
            if not self.is_valid_entity(entity_object):
                continue

            # Check area membership
            area_membership = await self._is_entity_from_area(entity_object)

            if not area_membership:
                continue

            entity_list.append(entity_object.entity_id)

        if include_entities and isinstance(include_entities, list):
            entity_list.extend(include_entities)

        self.load_entity_list(entity_list)

        self.logger.debug("%s: Loaded entities: %s", self.name, str(self.entities))

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
            if (
                self.id == META_AREA_GLOBAL.lower()
                or area.config.get(CONF_TYPE) == self.id
            ) and not area.is_meta():
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

        data = self.hass.data[MODULE_DATA]
        for area_info in data.values():
            area = area_info[DATA_AREA_OBJECT]
            if (
                self.id == META_AREA_GLOBAL.lower()
                or area.config.get(CONF_TYPE) == self.id
            ):
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
                        if entity["entity_id"] in self.config.get(
                            CONF_EXCLUDE_ENTITIES
                        ):
                            continue

                        entity_list.append(entity["entity_id"])

        self.load_entity_list(entity_list)

        self.logger.debug(
            "%s: Loaded entities for meta area: %s", self.name, str(self.entities)
        )
