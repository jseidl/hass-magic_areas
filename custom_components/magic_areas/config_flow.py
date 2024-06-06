"""Config Flow for Magic Area."""

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_DEVICE_CLASS, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.area_registry import async_get as areareg_async_get
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.floor_registry import async_get as floorreg_async_get
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    selector,
)
from homeassistant.util import slugify

from .const import (
    _DOMAIN_SCHEMA,
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_PRESENCE_DEVICE_PLATFORMS,
    ALL_SENSOR_DEVICE_CLASSES,
    AREA_STATE_DARK,
    AREA_STATE_EXTENDED,
    AREA_STATE_OCCUPIED,
    AREA_STATE_SLEEP,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    BUILTIN_AREA_STATES,
    CONF_ACCENT_ENTITY,
    CONF_ACCENT_LIGHTS,
    CONF_ACCENT_LIGHTS_ACT_ON,
    CONF_ACCENT_LIGHTS_STATES,
    CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES,
    CONF_AGGREGATES_ILLUMINANCE_THRESHOLD,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_AGGREGATES_SENSOR_DEVICE_CLASSES,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_GROUPS_TURN_ON_STATE,
    CONF_DARK_ENTITY,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_CLIMATE_GROUPS,
    CONF_FEATURE_HEALTH,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_HEALTH_SENSOR_DEVICE_CLASSES,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_OVERHEAD_LIGHTS,
    CONF_OVERHEAD_LIGHTS_ACT_ON,
    CONF_OVERHEAD_LIGHTS_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_LIGHTS_ACT_ON,
    CONF_SLEEP_LIGHTS_STATES,
    CONF_SLEEP_TIMEOUT,
    CONF_TASK_LIGHTS,
    CONF_TASK_LIGHTS_ACT_ON,
    CONF_TASK_LIGHTS_STATES,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONFIG_FLOW_ENTITY_FILTER_BOOL,
    CONFIG_FLOW_ENTITY_FILTER_EXT,
    CONFIGURABLE_AREA_STATE_MAP,
    CONFIGURABLE_FEATURES,
    DATA_AREA_OBJECT,
    DISTRESS_SENSOR_CLASSES,
    DOMAIN,
    LIGHT_GROUP_ACT_ON_OPTIONS,
    META_AREA_BASIC_OPTIONS_SCHEMA,
    META_AREA_GLOBAL,
    META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    META_AREA_SCHEMA,
    MODULE_DATA,
    NON_CONFIGURABLE_FEATURES_META,
    OPTIONS_AGGREGATES,
    OPTIONS_AREA,
    OPTIONS_AREA_AWARE_MEDIA_PLAYER,
    OPTIONS_AREA_META,
    OPTIONS_CLIMATE_GROUP,
    OPTIONS_CLIMATE_GROUP_META,
    OPTIONS_HEALTH_SENSOR,
    OPTIONS_LIGHT_GROUP,
    OPTIONS_PRESENCE_HOLD,
    OPTIONS_PRESENCE_TRACKING,
    OPTIONS_PRESENCE_TRACKING_META,
    OPTIONS_SECONDARY_STATES,
    REGULAR_AREA_BASIC_OPTIONS_SCHEMA,
    REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA,
    REGULAR_AREA_SCHEMA,
    SECONDARY_STATES_SCHEMA,
    MagicConfigEntryVersion,
    MetaAreaType,
)
from .util import basic_area_from_floor, basic_area_from_meta, basic_area_from_object

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class ConfigBase:
    """Base class for config flow."""

    config_entry = None

    # Selector builder
    def _build_selector_select(self, options=None, multiple=False):
        """Build a <select> selector."""
        if not options:
            options = []
        return selector(
            {"select": {"options": options, "multiple": multiple, "mode": "dropdown"}}
        )

    def _build_selector_entity_simple(
        self, options=None, multiple=False, force_include=False
    ):
        """Build a <select> selector with predefined settings."""
        if not options:
            options = []
        return NullableEntitySelector(
            EntitySelectorConfig(include_entities=options, multiple=multiple)
        )

    def _build_selector_number(
        self, min_value=0, max_value=9999, mode="box", unit_of_measurement="seconds"
    ):
        """Build a number selector."""
        return selector(
            {
                "number": {
                    "min": min_value,
                    "max": max_value,
                    "mode": mode,
                    "unit_of_measurement": unit_of_measurement,
                }
            }
        )

    def _build_options_schema(
        self,
        options,
        saved_options=None,
        dynamic_validators=None,
        selectors=None,
        raw=False,
    ):
        """Build schema for configuration options."""
        _LOGGER.debug(
            "ConfigFlow: Building schema from options: %s - dynamic_validators: %s",
            str(options),
            str(dynamic_validators),
        )

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if saved_options is None:
            saved_options = self.config_entry.options
        _LOGGER.debug(
            "ConfigFlow: Data for pre-populating fields: %s", str(saved_options)
        )

        schema = {
            vol.Optional(
                name,
                description={
                    "suggested_value": (
                        saved_options.get(name)
                        if saved_options.get(name) is not None
                        else default
                    )
                },
                default=default,
            ): (
                selectors[name]
                if name in selectors
                else dynamic_validators.get(name, validation)
            )
            for name, default, validation in options
        }

        _LOGGER.debug("ConfigFlow: Built schema: %s", str(schema))

        if raw:
            return schema

        return vol.Schema(schema)


class NullableEntitySelector(EntitySelector):
    """Entity selector that supports null values."""

    def __call__(self, data):
        """Validate the passed selection, if passed."""

        if data in (None, ""):
            return data

        return super().__call__(data)


class ConfigFlow(config_entries.ConfigFlow, ConfigBase, domain=DOMAIN):
    """Handle a config flow for Magic Areas."""

    VERSION = MagicConfigEntryVersion.MAJOR
    MINOR_VERSION = MagicConfigEntryVersion.MINOR

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        reserved_names = []
        non_floor_meta_areas = [
            meta_area_type
            for meta_area_type in MetaAreaType
            if meta_area_type != MetaAreaType.FLOOR
        ]

        # Load registries
        area_registry = areareg_async_get(self.hass)
        floor_registry = floorreg_async_get(self.hass)
        areas = [
            basic_area_from_object(area) for area in area_registry.async_list_areas()
        ]
        area_ids = [area.id for area in areas]

        # Load floors meta-aras
        floors = floor_registry.async_list_floors()

        for floor in floors:
            # Prevent conflicts between meta areas and existing areas
            if floor.floor_id in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    floor.floor_id,
                    floor.floor_id,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas",
                floor.floor_id,
            )
            area = basic_area_from_floor(floor)
            reserved_names.append(area.id)
            areas.append(area)

        # Add standard meta areas to area list
        for meta_area in non_floor_meta_areas:
            # Prevent conflicts between meta areas and existing areas
            if meta_area in area_ids:
                _LOGGER.warning(
                    "ConfigFlow: You have an area with a reserved name '%s'. This will prevent from using the %s Meta area.",
                    meta_area,
                    meta_area,
                )
                continue

            _LOGGER.debug(
                "ConfigFlow: Appending Meta Area %s to the list of areas", meta_area
            )
            area = basic_area_from_meta(meta_area)
            reserved_names.append(area.id)
            areas.append(area)

        if user_input is not None:
            # Look up area object by name
            area_object = None

            for area in areas:
                area_name = user_input[CONF_NAME]

                # Handle meta area name append
                if area_name.startswith("(Meta)"):
                    area_name = " ".join(area_name.split(" ")[1:])

                if area.name == area_name:
                    area_object = area
                    break

            # Fail if area name not found,
            # this should never happen in ideal conditions.
            if not area_object:
                return self.async_abort(reason="invalid_area")

            # Reserve unique name / already configured check
            await self.async_set_unique_id(area_object.id)
            self._abort_if_unique_id_configured()

            # Create area entry with default config
            config_entry = _DOMAIN_SCHEMA({f"{area_object.id}": {}})[area_object.id]
            extra_opts = {CONF_NAME: area_object.name, CONF_ID: area_object.id}
            config_entry.update(extra_opts)

            # Handle Meta area
            if slugify(area_object.id) in reserved_names:
                _LOGGER.debug(
                    "ConfigFlow: Meta area %s found, setting correct type.",
                    area_object.id,
                )
                config_entry.update({CONF_TYPE: AREA_TYPE_META})

            return self.async_create_entry(title=area_object.name, data=config_entry)

        # Filter out already-configured areas
        configured_areas = []
        ma_data = self.hass.data.get(MODULE_DATA, {})

        for config_data in ma_data.values():
            configured_areas.append(config_data[DATA_AREA_OBJECT].id)

        available_areas = [area for area in areas if area.id not in configured_areas]

        if not available_areas:
            return self.async_abort(reason="no_more_areas")

        # Slight ordering trick so Meta areas are at the bottom
        available_area_names = sorted(
            [area.name for area in available_areas if area.id not in reserved_names]
        )
        available_area_names.extend(
            sorted(
                [
                    f"(Meta) {area.name}"
                    for area in available_areas
                    if area.id in reserved_names
                ]
            )
        )

        schema = vol.Schema({vol.Required(CONF_NAME): vol.In(available_area_names)})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow, ConfigBase):
    """Handle a option flow for Adaptive Lighting."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.data = None
        self.area = None
        self.all_entities = []
        self.area_entities = []
        self.all_area_entities = []
        self.all_lights = []
        self.all_media_players = []
        self.all_binary_entities = []
        self.all_light_tracking_entities = []
        self.area_options = {}

    def _get_feature_list(self) -> list[str]:
        """Return list of available features for area type."""

        feature_list = CONF_FEATURE_LIST
        area_type = self.area.config.get(CONF_TYPE)
        if area_type == AREA_TYPE_META:
            feature_list = CONF_FEATURE_LIST_META
        if self.area.id == META_AREA_GLOBAL.lower():
            feature_list = CONF_FEATURE_LIST_GLOBAL

        return feature_list

    def _get_configurable_features(self) -> list[str]:
        """Return configurable features for area type."""
        filtered_configurable_features = list(CONFIGURABLE_FEATURES.keys())
        if self.area.is_meta():
            for feature in NON_CONFIGURABLE_FEATURES_META:
                if feature in filtered_configurable_features:
                    filtered_configurable_features.remove(feature)

        return filtered_configurable_features

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title="", data=dict(self.area_options))

    async def async_step_init(self, user_input=None):
        """Initialize the options flow."""

        self.data = self.hass.data[MODULE_DATA][self.config_entry.entry_id]
        self.area = self.data[DATA_AREA_OBJECT]

        _LOGGER.debug(
            "OptionsFlow: Initializing options flow for area %s", self.area.name
        )
        _LOGGER.debug(
            "OptionsFlow: Options in config entry for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        # Return all relevant entities
        self.all_entities = sorted(
            self.resolve_groups(
                entity_id
                for entity_id in self.hass.states.async_entity_ids()
                if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
            )
        )

        # Return all relevant area entities that exists
        # in self.all_entities
        filtered_area_entities = []
        for domain in CONFIG_FLOW_ENTITY_FILTER_EXT:
            filtered_area_entities.extend(
                [
                    entity["entity_id"]
                    for entity in self.area.entities.get(domain, [])
                    if entity["entity_id"] in self.all_entities
                ]
            )

        self.area_entities = sorted(self.resolve_groups(filtered_area_entities))

        # All binary entities
        self.all_binary_entities = sorted(
            self.resolve_groups(
                entity_id
                for entity_id in self.all_entities
                if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_BOOL
            )
        )

        self.all_area_entities = sorted(
            self.area_entities
            + self.config_entry.options.get(CONF_EXCLUDE_ENTITIES, [])
        )

        self.all_lights = sorted(
            self.resolve_groups(
                entity["entity_id"]
                for entity in self.area.entities.get(LIGHT_DOMAIN, [])
                if entity["entity_id"] in self.all_entities
            )
        )
        self.all_media_players = sorted(
            self.resolve_groups(
                entity["entity_id"]
                for entity in self.area.entities.get(MEDIA_PLAYER_DOMAIN, [])
                if entity["entity_id"] in self.all_entities
            )
        )

        # Compile all binary sensors of light device class
        eligible_light_tracking_entities = []
        for entity in self.all_entities:
            e_component = entity.split(".")[0]

            if e_component == BINARY_SENSOR_DOMAIN:
                entity_object = self.hass.states.get(entity)
                entity_object_attributes = entity_object.attributes
                if (
                    ATTR_DEVICE_CLASS in entity_object_attributes
                    and entity_object_attributes[ATTR_DEVICE_CLASS]
                    == BinarySensorDeviceClass.LIGHT
                ):
                    eligible_light_tracking_entities.append(entity)

        # Add additional entities to eligitible entities
        eligible_light_tracking_entities.extend(ADDITIONAL_LIGHT_TRACKING_ENTITIES)

        self.all_light_tracking_entities = sorted(
            self.resolve_groups(eligible_light_tracking_entities)
        )

        area_schema = META_AREA_SCHEMA if self.area.is_meta() else REGULAR_AREA_SCHEMA
        self.area_options = area_schema(dict(self.config_entry.options))

        _LOGGER.debug(
            "%s: Loaded area options: %s", self.area.name, str(self.area_options)
        )

        return await self.async_step_show_menu()

    async def async_step_show_menu(self, user_input=None):
        """Show options selection menu."""
        # Show options menu
        menu_options: list = [
            "area_config",
            "presence_tracking",
            "select_features",
        ]

        if not self.area.is_meta():
            menu_options.insert(1, "secondary_states")

        # Add entries for features
        menu_options_features = []
        configurable_features = self._get_configurable_features()
        for feature in self.area_options.get(CONF_ENABLED_FEATURES, {}):
            if feature not in configurable_features:
                continue
            menu_options_features.append(f"feature_conf_{feature}")

        menu_options.extend(sorted(menu_options_features))
        menu_options.append("finish")

        return self.async_show_menu(step_id="show_menu", menu_options=menu_options)

    @staticmethod
    def resolve_groups(raw_list):
        """Resolve entities from groups."""
        resolved_list = []
        for item in raw_list:
            if isinstance(item, list):
                for item_child in item:
                    resolved_list.append(item_child)
                continue
            resolved_list.append(item)

        return list(dict.fromkeys(resolved_list))

    async def async_step_area_config(self, user_input=None):
        """Gather basic settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s base config: %s",
                self.area.name,
                str(user_input),
            )
            options_schema = (
                META_AREA_BASIC_OPTIONS_SCHEMA
                if self.area.is_meta()
                else REGULAR_AREA_BASIC_OPTIONS_SCHEMA
            )
            try:
                self.area_options.update(options_schema(user_input))
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area %s base config: %s",
                    self.area.name,
                    str(self.area_options),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            CONF_TYPE: self._build_selector_select(
                sorted([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR])
            ),
            CONF_INCLUDE_ENTITIES: self._build_selector_entity_simple(
                self.all_entities, multiple=True
            ),
            CONF_EXCLUDE_ENTITIES: self._build_selector_entity_simple(
                self.all_area_entities, multiple=True
            ),
        }

        options = OPTIONS_AREA_META if self.area.is_meta() else OPTIONS_AREA
        selectors = {}

        # Apply options for given area type (regular/meta)
        option_keys = [option[0] for option in options]
        for option_key in option_keys:
            selectors[option_key] = all_selectors[option_key]

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        return self.async_show_form(
            step_id="area_config",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_presence_tracking(self, user_input=None):
        """Gather basic settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s presence tracking config: %s",
                self.area.name,
                str(user_input),
            )
            options_schema = (
                META_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
                if self.area.is_meta()
                else REGULAR_AREA_PRESENCE_TRACKING_OPTIONS_SCHEMA
            )
            try:
                self.area_options.update(options_schema(user_input))
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught on area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area %s base config: %s",
                    self.area.name,
                    str(self.area_options),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            CONF_PRESENCE_DEVICE_PLATFORMS: self._build_selector_select(
                sorted(ALL_PRESENCE_DEVICE_PLATFORMS), multiple=True
            ),
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: self._build_selector_select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            CONF_UPDATE_INTERVAL: self._build_selector_number(
                unit_of_measurement="seconds"
            ),
            CONF_CLEAR_TIMEOUT: self._build_selector_number(
                unit_of_measurement="minutes"
            ),
        }

        options = (
            OPTIONS_PRESENCE_TRACKING_META
            if self.area.is_meta()
            else OPTIONS_PRESENCE_TRACKING
        )
        selectors = {}

        # Apply options for given area type (regular/meta)
        option_keys = [option[0] for option in options]
        for option_key in option_keys:
            selectors[option_key] = all_selectors[option_key]

        data_schema = self._build_options_schema(
            options=options, saved_options=self.area_options, selectors=selectors
        )

        return self.async_show_form(
            step_id="presence_tracking",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_secondary_states(self, user_input=None):
        """Gather secondary states settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating area %s secondary states config: %s",
                self.area.name,
                str(user_input),
            )
            area_state_schema = SECONDARY_STATES_SCHEMA
            try:
                self.area_options[CONF_SECONDARY_STATES].update(
                    area_state_schema(user_input)
                )
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug(
                    "OptionsFlow: Found the following errors for area %s: %s",
                    self.area.name,
                    str(errors),
                )
            # Adding pylint exception because this is a last-resort hail-mary catch-all
            # pylint: disable-next=broad-exception-caught
            except Exception as e:
                _LOGGER.warning(
                    "OptionsFlow: Unexpected error caught for area %s: %s",
                    self.area.name,
                    str(e),
                )
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving area secondary state config for area %s: %s",
                    self.area.name,
                    str(self.area_options),
                )
                return await self.async_step_show_menu()

        return self.async_show_form(
            step_id="secondary_states",
            data_schema=self._build_options_schema(
                options=(OPTIONS_SECONDARY_STATES),
                saved_options=self.area_options.get(CONF_SECONDARY_STATES, {}),
                dynamic_validators={
                    CONF_DARK_ENTITY: vol.In(
                        EMPTY_ENTRY + self.all_light_tracking_entities
                    ),
                    CONF_SLEEP_ENTITY: vol.In(EMPTY_ENTRY + self.all_binary_entities),
                    CONF_ACCENT_ENTITY: vol.In(EMPTY_ENTRY + self.all_binary_entities),
                },
                selectors={
                    CONF_DARK_ENTITY: self._build_selector_entity_simple(
                        self.all_light_tracking_entities
                    ),
                    CONF_SLEEP_ENTITY: self._build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_ACCENT_ENTITY: self._build_selector_entity_simple(
                        self.all_binary_entities
                    ),
                    CONF_SLEEP_TIMEOUT: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIME: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                    CONF_EXTENDED_TIMEOUT: self._build_selector_number(
                        unit_of_measurement="minutes"
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_select_features(self, user_input=None):
        """Ask the user to select features to enable for the area."""

        feature_list = self._get_feature_list()

        if user_input is not None:
            selected_features = [
                feature for feature, is_selected in user_input.items() if is_selected
            ]

            _LOGGER.debug(
                "OptionsFlow: Selected features for area %s: %s",
                self.area.name,
                str(selected_features),
            )

            if CONF_ENABLED_FEATURES not in self.area_options:
                self.area_options[CONF_ENABLED_FEATURES] = {}

            for c_feature in feature_list:
                if c_feature in selected_features:
                    if c_feature not in self.area_options.get(
                        CONF_ENABLED_FEATURES, {}
                    ):
                        self.area_options[CONF_ENABLED_FEATURES][c_feature] = {}
                else:
                    # Remove feature if we had previously enabled
                    if c_feature in self.area_options.get(CONF_ENABLED_FEATURES, {}):
                        self.area_options[CONF_ENABLED_FEATURES].pop(c_feature)

            return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Selecting features for area %s from %s",
            self.area.name,
            feature_list,
        )

        return self.async_show_form(
            step_id="select_features",
            data_schema=self._build_options_schema(
                options=[(feature, False, bool) for feature in feature_list],
                saved_options={
                    feature: (
                        feature in self.area_options.get(CONF_ENABLED_FEATURES, {})
                    )
                    for feature in feature_list
                },
            ),
        )

    async def async_step_finish(self, user_input=None):
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self.area.name,
            str(self.area_options),
        )
        return await self._update_options()

    async def async_step_feature_conf_light_groups(self, user_input=None):
        """Configure the light groups feature."""

        available_states = BUILTIN_AREA_STATES.copy()

        light_group_state_exempt = [AREA_STATE_DARK]
        for extra_state, extra_state_entity in CONFIGURABLE_AREA_STATE_MAP.items():
            # Skip AREA_STATE_DARK because lights can't be tied to this state
            if extra_state in light_group_state_exempt:
                continue

            if self.area_options[CONF_SECONDARY_STATES].get(extra_state_entity, None):
                available_states.append(extra_state)

        return await self.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS,
            options=OPTIONS_LIGHT_GROUP,
            dynamic_validators={
                CONF_OVERHEAD_LIGHTS: cv.multi_select(self.all_lights),
                CONF_OVERHEAD_LIGHTS_STATES: cv.multi_select(available_states),
                CONF_OVERHEAD_LIGHTS_ACT_ON: cv.multi_select(
                    LIGHT_GROUP_ACT_ON_OPTIONS
                ),
                CONF_SLEEP_LIGHTS: cv.multi_select(self.all_lights),
                CONF_SLEEP_LIGHTS_STATES: cv.multi_select(available_states),
                CONF_SLEEP_LIGHTS_ACT_ON: cv.multi_select(LIGHT_GROUP_ACT_ON_OPTIONS),
                CONF_ACCENT_LIGHTS: cv.multi_select(self.all_lights),
                CONF_ACCENT_LIGHTS_STATES: cv.multi_select(available_states),
                CONF_ACCENT_LIGHTS_ACT_ON: cv.multi_select(LIGHT_GROUP_ACT_ON_OPTIONS),
                CONF_TASK_LIGHTS: cv.multi_select(self.all_lights),
                CONF_TASK_LIGHTS_STATES: cv.multi_select(available_states),
                CONF_TASK_LIGHTS_ACT_ON: cv.multi_select(LIGHT_GROUP_ACT_ON_OPTIONS),
            },
            selectors={
                CONF_OVERHEAD_LIGHTS: self._build_selector_entity_simple(
                    self.all_lights, multiple=True
                ),
                CONF_OVERHEAD_LIGHTS_STATES: self._build_selector_select(
                    available_states, multiple=True
                ),
                CONF_OVERHEAD_LIGHTS_ACT_ON: self._build_selector_select(
                    LIGHT_GROUP_ACT_ON_OPTIONS, multiple=True
                ),
                CONF_SLEEP_LIGHTS: self._build_selector_entity_simple(
                    self.all_lights, multiple=True
                ),
                CONF_SLEEP_LIGHTS_STATES: self._build_selector_select(
                    available_states, multiple=True
                ),
                CONF_SLEEP_LIGHTS_ACT_ON: self._build_selector_select(
                    LIGHT_GROUP_ACT_ON_OPTIONS, multiple=True
                ),
                CONF_ACCENT_LIGHTS: self._build_selector_entity_simple(
                    self.all_lights, multiple=True
                ),
                CONF_ACCENT_LIGHTS_STATES: self._build_selector_select(
                    available_states, multiple=True
                ),
                CONF_ACCENT_LIGHTS_ACT_ON: self._build_selector_select(
                    LIGHT_GROUP_ACT_ON_OPTIONS, multiple=True
                ),
                CONF_TASK_LIGHTS: self._build_selector_entity_simple(
                    self.all_lights, multiple=True
                ),
                CONF_TASK_LIGHTS_STATES: self._build_selector_select(
                    available_states, multiple=True
                ),
                CONF_TASK_LIGHTS_ACT_ON: self._build_selector_select(
                    LIGHT_GROUP_ACT_ON_OPTIONS, multiple=True
                ),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_climate_groups(self, user_input=None):
        """Configure the climate groups feature."""

        available_states = [AREA_STATE_OCCUPIED, AREA_STATE_EXTENDED]

        return await self.do_feature_config(
            name=CONF_FEATURE_CLIMATE_GROUPS,
            options=(
                OPTIONS_CLIMATE_GROUP
                if not self.area.is_meta()
                else OPTIONS_CLIMATE_GROUP_META
            ),
            dynamic_validators={
                CONF_CLIMATE_GROUPS_TURN_ON_STATE: vol.In(
                    EMPTY_ENTRY + available_states
                ),
            },
            selectors={
                CONF_CLIMATE_GROUPS_TURN_ON_STATE: self._build_selector_select(
                    EMPTY_ENTRY + available_states
                )
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_health(self, user_input=None):
        """Configure the climate groups feature."""

        return await self.do_feature_config(
            name=CONF_FEATURE_HEALTH,
            options=OPTIONS_HEALTH_SENSOR,
            dynamic_validators={
                CONF_HEALTH_SENSOR_DEVICE_CLASSES: vol.In(
                    EMPTY_ENTRY + DISTRESS_SENSOR_CLASSES
                ),
            },
            selectors={
                CONF_HEALTH_SENSOR_DEVICE_CLASSES: self._build_selector_select(
                    EMPTY_ENTRY + DISTRESS_SENSOR_CLASSES, multiple=True
                )
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_area_aware_media_player(self, user_input=None):
        """Configure the area aware media player feature."""

        available_states = [AREA_STATE_OCCUPIED, AREA_STATE_EXTENDED, AREA_STATE_SLEEP]

        return await self.do_feature_config(
            name=CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
            options=OPTIONS_AREA_AWARE_MEDIA_PLAYER,
            dynamic_validators={
                CONF_NOTIFICATION_DEVICES: cv.multi_select(self.all_media_players),
                CONF_NOTIFY_STATES: cv.multi_select(available_states),
            },
            selectors={
                CONF_NOTIFICATION_DEVICES: self._build_selector_entity_simple(
                    self.all_media_players, multiple=True
                ),
                CONF_NOTIFY_STATES: self._build_selector_select(
                    available_states, multiple=True
                ),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_aggregates(self, user_input=None):
        """Configure the sensor aggregates feature."""

        selectors = {
            CONF_AGGREGATES_MIN_ENTITIES: self._build_selector_number(
                unit_of_measurement="entities"
            ),
            CONF_AGGREGATES_BINARY_SENSOR_DEVICE_CLASSES: self._build_selector_select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            CONF_AGGREGATES_SENSOR_DEVICE_CLASSES: self._build_selector_select(
                sorted(ALL_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            CONF_AGGREGATES_ILLUMINANCE_THRESHOLD: self._build_selector_number(
                unit_of_measurement="lx", mode="slider", min_value=0, max_value=1000
            ),
        }

        return await self.do_feature_config(
            name=CONF_FEATURE_AGGREGATION,
            options=OPTIONS_AGGREGATES,
            selectors=selectors,
            user_input=user_input,
        )

    async def async_step_feature_conf_presence_hold(self, user_input=None):
        """Configure the sensor presence_hold feature."""

        selectors = {
            CONF_PRESENCE_HOLD_TIMEOUT: self._build_selector_number(
                min_value=0, unit_of_measurement="minutes"
            )
        }

        return await self.do_feature_config(
            name=CONF_FEATURE_PRESENCE_HOLD,
            options=OPTIONS_PRESENCE_HOLD,
            selectors=selectors,
            user_input=user_input,
        )

    async def do_feature_config(
        self, name, options, dynamic_validators=None, selectors=None, user_input=None
    ):
        """Execute step for a generic feature."""
        errors = {}

        if not dynamic_validators:
            dynamic_validators = {}

        if not selectors:
            selectors = {}

        if user_input is not None:
            _LOGGER.debug(
                "OptionsFlow: Validating %s feature config for area %s: %s",
                name,
                self.area.name,
                str(user_input),
            )
            try:
                validated_input = CONFIGURABLE_FEATURES[name](user_input)
            except vol.MultipleInvalid as validation:
                errors = {
                    error.path[0]: "malformed_input" for error in validation.errors
                }
                _LOGGER.debug("OptionsFlow: Found the following errors: %s", errors)
            else:
                _LOGGER.debug(
                    "OptionsFlow: Saving %s feature config for area %s: %s",
                    name,
                    self.area.name,
                    str(validated_input),
                )
                self.area_options[CONF_ENABLED_FEATURES][name] = validated_input
                return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Config entry options for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        saved_options = self.area_options.get(CONF_ENABLED_FEATURES, {})

        return self.async_show_form(
            step_id=f"feature_conf_{name}",
            data_schema=self._build_options_schema(
                options=options,
                saved_options=saved_options.get(name, {}),
                dynamic_validators=dynamic_validators,
                selectors=selectors,
            ),
            errors=errors,
        )
