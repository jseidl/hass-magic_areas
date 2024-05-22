"""The device setup for the magic areas."""

from dataclasses import dataclass
from datetime import UTC, datetime
import logging

from custom_components.simply_magic_areas.const import (
    ALL_LIGHT_ENTITIES,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    CONF_INCLUDE_ENTITIES,
    CONF_TYPE,
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
    AreaState,
)
from custom_components.simply_magic_areas.util import (
    areas_loaded,
    flatten_entity_list,
    is_entity_list,
)
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import AreaEntry
from homeassistant.helpers.device_registry import async_get as async_get_dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
    RegistryEntry,
    async_get as async_get_er,
)
from homeassistant.util import slugify
from homeassistant.util.event_type import EventType

_LOGGER = logging.getLogger(__name__)


@dataclass
class MagicEvent:
    """The data for magic area events."""

    id: str


@dataclass
class StateConfigData:
    """The read config data about the light for each state."""

    name: str
    entity: str | None
    entity_state_on: str
    dim_level: int
    for_state: AreaState
    icon: str
    manual_entity: str
    control_entity: str
    lights: list[str]


class MagicArea(object):  # noqa: UP004
    """The base class for the magic area integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        area: AreaEntry,
        config: ConfigEntry,
        listen_event: EventType = EVENT_HOMEASSISTANT_STARTED,
        init_on_hass_running: bool = True,
    ) -> None:
        """Initialize the magic area with all the stuff."""
        self.hass: HomeAssistant = hass
        self.name: str = area.name
        # Default to the icon for the area.
        self.icon: str = area.icon
        self.id: str = area.id
        self.slug: str = slugify(self.name)
        self.hass_config: ConfigEntry = config
        self.initialized: bool = False

        # Merged options
        area_config = dict(config.data)
        if config.options:
            area_config.update(config.options)
        self.config = area_config

        self.entities = {}

        self.last_changed: int = datetime.now(UTC)
        self.state: AreaState = AreaState.AREA_STATE_CLEAR
        self._state_config: dict[AreaState, StateConfigData] = {}

        self.loaded_platforms: list[str] = []

        # Add callback for initialization
        if self.hass.is_running and init_on_hass_running:
            self.hass.async_create_task(self._initialize())
        else:
            self.hass.bus.async_listen_once(listen_event, self._initialize)

        _LOGGER.debug("%s: Area Primed for initialization", self.slug)

    def _finalize_init(self) -> None:
        self.initialized = True

        self.hass.bus.async_fire(EVENT_MAGICAREAS_AREA_READY, {"id": self.id})

        if not self.is_meta():
            # Check if we finished loading all areas
            if areas_loaded(self.hass):
                self.hass.bus.async_fire(EVENT_MAGICAREAS_READY)

        area_type = "Meta-Area" if self.is_meta() else "Area"
        _LOGGER.debug("%s: %s initialized", self.slug, area_type)

    def is_occupied(self) -> bool:
        """If the area is occupied."""
        return self.state != AreaState.AREA_STATE_CLEAR

    def is_bright(self) -> bool:
        """If the area is in the bright state."""
        return self.state == AreaState.AREA_STATE_BRIGHT

    def is_sleep(self) -> bool:
        """If the area is in the sleep state."""
        return self.state == AreaState.AREA_STATE_SLEEP

    def is_extended(self) -> bool:
        """IF the area is in the extended state."""
        return self.state == AreaState.AREA_STATE_EXTENDED

    def state_config(self, state: AreaState) -> StateConfigData | None:
        """Return the light entity config for the current state."""
        return self._state_config[state]

    def all_state_configs(self) -> dict[AreaState, StateConfigData]:
        """Return the dictionary with all the currently configured state configs."""
        return self._state_config

    def has_configured_state(self, state: AreaState) -> bool:
        """If the area has the specified configured state."""
        return state in self._state_config

    def has_feature(self, feature: str) -> bool:
        """If the area has the specified feature."""
        enabled_features = self.config.get(CONF_ENABLED_FEATURES, {})

        # Handle everything else
        if not isinstance(enabled_features, dict):
            _LOGGER.warning(
                "%s: Invalid configuration for %s",
                self.name,
                CONF_ENABLED_FEATURES,
            )
            return False

        return feature in enabled_features

    def feature_config(self, feature: str) -> dict:
        """Get the feature config for the specified feature."""
        if not self.has_feature(feature):
            _LOGGER.debug("%s: Feature %s not enabled", self.name, feature)
            return {}

        options = self.config.get(CONF_ENABLED_FEATURES, {})

        if not options:
            _LOGGER.debug("%s: No feature config found for %s", self.name, feature)

        return options.get(feature, {})

    def available_platforms(self) -> list[str]:
        """Return the available platforms for this area."""
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
    def area_type(self) -> str:
        """Type type of the area."""
        return self.config.get(CONF_TYPE)

    def is_meta(self) -> bool:
        """If this is a meta area."""
        return self.area_type == AREA_TYPE_META

    def is_interior(self):
        """If this is an interior area."""
        return self.area_type == AREA_TYPE_INTERIOR

    def is_exterior(self):
        """If this is an exterior area."""
        return self.area_type == AREA_TYPE_EXTERIOR

    def _is_magic_area_entity(self, entity_object: RegistryEntry) -> bool:
        if entity_object.device_id:
            device_registry = async_get_dr(self.hass)
            device_object = device_registry.async_get(entity_object.device_id)

            if device_object:
                our_device_tuple = (DOMAIN, f"{MAGIC_DEVICE_ID_PREFIX}{self.id}")

                if our_device_tuple in device_object.identifiers:
                    _LOGGER.debug(
                        "%s: Entity %s is ours, skipping",
                        self.name,
                        entity_object.entity_id,
                    )
                    return True
        return False

    def _is_valid_entity(self, entity_object: RegistryEntry) -> bool:
        # Ignore our own entities
        if self._is_magic_area_entity(entity_object):
            return False

        if entity_object.disabled:
            return False

        if entity_object.entity_id in self.feature_config(
            CONF_FEATURE_ADVANCED_LIGHT_GROUPS
        ).get(CONF_EXCLUDE_ENTITIES, []):
            return False

        return True

    async def _is_entity_from_area(self, entity_object) -> bool:
        # Check entity's area_id
        if entity_object.area_id == self.id:
            return True

        # Check device's area id, if available
        if entity_object.device_id:
            device_registry = async_get_dr(self.hass)
            if entity_object.device_id in device_registry.devices:
                device_object = device_registry.devices[entity_object.device_id]
                if device_object.area_id == self.id:
                    return True

        # Check if entity_id is in CONF_INCLUDE_ENTITIES
        if entity_object.entity_id in self.feature_config(
            CONF_FEATURE_ADVANCED_LIGHT_GROUPS
        ).get(CONF_INCLUDE_ENTITIES, []):
            return True

        return False

    async def _load_entities(self) -> None:
        entity_list = []
        magic_area_entities = []
        include_entities = self.feature_config(CONF_FEATURE_ADVANCED_LIGHT_GROUPS).get(
            CONF_INCLUDE_ENTITIES, []
        )

        entity_registry = async_get_er(self.hass)

        for entity_object in entity_registry.entities.values():
            if self._is_magic_area_entity(entity_object):
                magic_area_entities.append(entity_object.entity_id)
                continue

            # Check entity validity
            if not self._is_valid_entity(entity_object):
                continue

            # Check area membership
            area_membership = await self._is_entity_from_area(entity_object)

            if not area_membership:
                continue

            entity_list.append(entity_object.entity_id)

        if include_entities and isinstance(include_entities, list):
            entity_list.extend(include_entities)

        self._load_entity_list("", entity_list)
        self._load_entity_list(DOMAIN, magic_area_entities)

        _LOGGER.debug("%s: Loaded entities for area  %s", self.slug, self.entities)

    def _load_entity_list(self, prefix: str, entity_list: list[str]) -> None:
        flattened_entity_list = flatten_entity_list(entity_list)
        unique_entities = set(flattened_entity_list)
        for entity_id in unique_entities:
            try:
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
                    _LOGGER.debug(
                        "%s: %s is probably a group, skipping",
                        self.slug,
                        entity_id,
                    )
                    continue

                if prefix + entity_component not in self.entities:
                    self.entities[prefix + entity_component] = []

                self.entities[prefix + entity_component].append(updated_entity)

            except Exception as err:  # noqa: BLE001
                _LOGGER.error(
                    "%s: Unable to load entity '%s': {%s}",
                    self.slug,
                    entity_id,
                    str(err),
                )

    async def _initialize(self, _=None) -> None:
        _LOGGER.debug("%s: Initializing area", self.slug)

        await self._load_entities()

        await self._load_state_config()

        self._finalize_init()

    def has_entities(self, domain: str) -> bool:
        """Check and see if this areas has entites with the specified domain."""
        return domain in self.entities

    async def _load_state_config(self) -> None:
        light_entities = []
        if LIGHT_DOMAIN in self.entities:
            light_entities = [e["entity_id"] for e in self.entities[LIGHT_DOMAIN]]

        for lg in ALL_LIGHT_ENTITIES:
            entity_ob: str | None = None
            base = self.config
            if lg.is_advanced:
                base = self.feature_config(CONF_FEATURE_ADVANCED_LIGHT_GROUPS)
            if lg.has_entity:
                entity_ob = base.get(lg.entity_name())
                if entity_ob is None:
                    continue
            lights = self.feature_config(CONF_FEATURE_ADVANCED_LIGHT_GROUPS).get(
                lg.advanced_lights_to_control(), light_entities
            )
            if not lights:
                lights = light_entities
            self._state_config[lg.enable_state] = StateConfigData(
                name=lg.name,
                entity=entity_ob,
                entity_state_on=self.feature_config(
                    CONF_FEATURE_ADVANCED_LIGHT_GROUPS
                ).get(lg.advanced_state_check(), "on"),
                dim_level=int(base.get(lg.state_dim_level(), lg.default_dim_level)),
                for_state=lg.enable_state,
                icon=lg.icon,
                control_entity=f"{SWITCH_DOMAIN}.area_light_control_{self.slug}",
                manual_entity=f"{SWITCH_DOMAIN}.area_manual_override_active_{self.slug}",
                lights=lights,
            )


class MagicMetaArea(MagicArea):
    """Class for the meta magic areas that contain other areas."""

    def __init__(
        self, hass: HomeAssistant, area: AreaEntry, config: ConfigEntry
    ) -> None:
        """Initialize the meta magic area."""
        super().__init__(
            hass,
            area,
            config,
            EVENT_MAGICAREAS_READY,
            init_on_hass_running=areas_loaded(hass),
        )

    def _areas_loaded(self, hass: HomeAssistant = None) -> bool:
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

    def get_active_areas(self) -> list[MagicArea]:
        """Get the currently active areas."""
        areas = self.get_child_areas()
        active_areas = []

        for area in areas:
            try:
                entity_id = f"binary_sensor.area_{area}"
                entity = self.hass.states.get(entity_id)

                if entity.state == STATE_ON:
                    active_areas.append(area)
            except Exception as e:  # noqa: BLE001
                _LOGGER.error(
                    "%s: Unable to get active area state for %s: %s",
                    self.slug,
                    area,
                    str(e),
                )

        return active_areas

    def get_child_areas(self) -> list[MagicArea]:
        """Get the child areas."""
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

    async def _initialize(self, _=None) -> None:
        if self.initialized:
            _LOGGER.warning("%s: Meta-Area Already initialized, ignoring", self.name)
            return False

        # Meta-areas need to wait until other magic areas are loaded.
        if not self._areas_loaded():
            _LOGGER.warning(
                "%s: Meta-Area Non-meta areas not loaded. This shouldn't happen",
                self.name,
            )
            return False

        _LOGGER.debug("%s: Initializing meta area", self.name)

        await self._load_entities()

        self._finalize_init()

    async def _load_entities(self) -> None:
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
                            _LOGGER.debug(
                                "%s: Entity ID is not a string: %s (probably a group, skipping)",
                                self.slug,
                                entity["entity_id"],
                            )
                            continue

                        # Skip excluded entities
                        if entity["entity_id"] in self.self.feature_config(
                            CONF_FEATURE_ADVANCED_LIGHT_GROUPS
                        ).get(CONF_EXCLUDE_ENTITIES, []):
                            continue

                        entity_list.append(entity["entity_id"])

        self._load_entity_list(entity_list)

        _LOGGER.debug("%s: Loaded entities for meta area %s", self.slug, self.entities)
