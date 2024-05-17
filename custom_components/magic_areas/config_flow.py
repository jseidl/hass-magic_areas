"""Configuration flow for the magic areas component."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.area_registry import async_get as async_get_ar
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import EntitySelectorConfig, Selector, selector

from .const import (
    _DOMAIN_SCHEMA,
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_LIGHT_ENTITIES,
    ALL_PRESENCE_DEVICE_PLATFORMS,
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    AVAILABLE_ON_STATES,
    CONF_AGGREGATES_MIN_ENTITIES,
    CONF_CLEAR_TIMEOUT,
    CONF_CLIMATE_GROUPS_TURN_ON_STATE,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
    CONF_FEATURE_AGGREGATION,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_CLIMATE_GROUPS,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_PRESENCE_HOLD,
    CONF_ICON,
    CONF_ID,
    CONF_INCLUDE_ENTITIES,
    CONF_NOTIFICATION_DEVICES,
    CONF_NOTIFY_STATES,
    CONF_ON_STATES,
    CONF_PRESENCE_DEVICE_PLATFORMS,
    CONF_PRESENCE_HOLD_TIMEOUT,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SECONDARY_STATES,
    CONF_TYPE,
    CONF_UPDATE_INTERVAL,
    CONFIG_FLOW_ENTITY_FILTER_EXT,
    CONFIGURABLE_FEATURES,
    DATA_AREA_OBJECT,
    DEFAULT_ICON,
    DOMAIN,
    META_AREA_GLOBAL,
    META_AREA_SCHEMA,
    META_AREAS,
    MODULE_DATA,
    NON_CONFIGURABLE_FEATURES_META,
    OPTIONS_AGGREGATES,
    OPTIONS_AREA,
    OPTIONS_AREA_AWARE_MEDIA_PLAYER,
    OPTIONS_AREA_META,
    OPTIONS_CLIMATE_GROUP,
    OPTIONS_CLIMATE_GROUP_META,
    OPTIONS_PRESENCE_HOLD,
    REGULAR_AREA_SCHEMA,
    SECONDARY_STATES_SCHEMA,
    AreaState,
)
from .nullable_entity_selector import NullableEntitySelector
from .util import get_meta_area_object

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class ConfigBase:
    """Base object for the magic areas config."""

    # Selector builder
    def _build_selector_select(
        self, options: list[str] | None = None, multiple: bool = False
    ) -> Selector:
        if options is None:
            return selector(
                {
                    "select": {
                        "options": [],
                        "multiple": multiple,
                        "mode": "dropdown",
                    }
                }
            )

        return selector(
            {"select": {"options": options, "multiple": multiple, "mode": "dropdown"}}
        )

    def _build_selector_entity_simple(
        self,
        options: list[str] | None = None,
        multiple: bool = False,
    ) -> Selector:
        if options is None:
            return NullableEntitySelector(
                EntitySelectorConfig(include_entities=[], multiple=multiple)
            )

        return NullableEntitySelector(
            EntitySelectorConfig(include_entities=options, multiple=multiple)
        )

    def _build_selector_number(
        self,
        min: int = 0,
        max: int = 9999,
        mode: str = "box",
        unit_of_measurement: str = "seconds",
        initial: int = 0,
    ) -> Selector:
        return selector(
            {
                "number": {
                    "initial": initial,
                    "min": min,
                    "max": max,
                    "mode": mode,
                    "unit_of_measurement": unit_of_measurement,
                }
            }
        )

    def _build_options_schema(
        self,
        options: list[str],
        saved_options: list[str] | None = None,
        dynamic_validators: dict | None = None,
        selectors: dict | None = None,
        raw: bool = False,
    ) -> Selector:
        _LOGGER.debug(
            "Building schema from options: %s - dynamic_validators: %s",
            options,
            dynamic_validators,
        )
        if saved_options is None:
            saved_options = self.config_entry.options
        _LOGGER.debug("Data for pre-populating fields: %s", saved_options)

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

        _LOGGER.debug("Built schema: %s", schema)

        if raw:
            return schema
        return vol.Schema(schema)


class ConfigFlow(config_entries.ConfigFlow, ConfigBase, domain=DOMAIN):
    """Handle a config flow for Magic Areas."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors = {}

        reserved_names = [meta_area.lower() for meta_area in META_AREAS]

        # Load registries

        area_registry = async_get_ar(self.hass)
        areas = list(area_registry.async_list_areas())
        area_ids = [area.id for area in areas]

        # Add Meta Areas to area list
        for meta_area in META_AREAS:
            # Prevent conflicts between meta areas and existing areas
            if meta_area.lower() in area_ids:
                _LOGGER.warning(
                    "You have an area with a reserved name %s. This will prevent from using the %s Meta area",
                    meta_area,
                    meta_area,
                )
                continue

            _LOGGER.debug("Appending Meta Area %s to the list of areas", meta_area)
            areas.append(get_meta_area_object(meta_area))

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
            if area_object.normalized_name in reserved_names:
                _LOGGER.debug(
                    "Meta area %s found, setting correct type", area_object.name
                )
                config_entry.update({CONF_TYPE: AREA_TYPE_META})

            return self.async_create_entry(
                title=user_input[CONF_NAME], data=config_entry
            )

        # Filter out already-configured areas
        configured_areas = []
        ma_data = self.hass.data.get(MODULE_DATA, {})

        for config_data in ma_data.values():
            configured_areas.append(config_data[DATA_AREA_OBJECT].id)  # noqa: PERF401

        available_areas = [area for area in areas if area.id not in configured_areas]

        if not available_areas:
            return self.async_abort(reason="no_more_areas")

        # Slight ordering trick so Meta areas are at the bottom
        available_area_names = sorted(
            [
                area.name
                for area in available_areas
                if area.normalized_name not in reserved_names
            ]
        )
        available_area_names.extend(
            sorted(
                [
                    f"(Meta) {area.name}"
                    for area in available_areas
                    if area.normalized_name in reserved_names
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

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry: config_entries.ConfigEntry = config_entry
        self.data = None
        self.area = None
        self.all_entities: list[str] = []
        self.area_entities: list[str] = []
        self.all_area_entities: list[str] = []
        self.all_lights: list[str] = []
        self.all_media_players: list[str] = []
        self.selected_features: list[str] = []
        self.features_to_configure: list[str] | None = None
        self.area_options: vol.Schema | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> None:
        """Initialize the options flow."""
        self.data = self.hass.data[MODULE_DATA][self.config_entry.entry_id]
        self.area = self.data[DATA_AREA_OBJECT]

        _LOGGER.debug("Initializing options flow for area %s", self.area.name)
        _LOGGER.debug("Options in config entry: %s", self.config_entry.options)

        # Return all relevant entities
        self.all_entities = sorted(
            entity_id
            for entity_id in self.hass.states.async_entity_ids()
            if entity_id.split(".")[0] in CONFIG_FLOW_ENTITY_FILTER_EXT
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

        return await self.async_step_area_config()

    @staticmethod
    def resolve_groups(raw_list) -> list[str]:
        """Resolve entities from groups."""
        resolved_list = []
        for item in raw_list:
            if isinstance(item, list):
                for item_child in item:
                    resolved_list.append(item_child)
                continue
            resolved_list.append(item)

        return list(dict.fromkeys(resolved_list))

    async def async_step_area_config(self, user_input: str | None = None) -> None:
        """Gather basic settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("Validating area base config: %s", user_input)
            area_schema = (
                META_AREA_SCHEMA if self.area.is_meta() else REGULAR_AREA_SCHEMA
            )
            try:
                self.area_options = area_schema(user_input)
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug("Found the following errors: %s", errors)
            except Exception as e:
                _LOGGER.warning("Unexpected error caught: %s", str(e))
            else:
                _LOGGER.debug("Saving area base config: %s", self.area_options)
                if self.area.is_meta():
                    return await self.async_step_select_features()
                return await self.async_step_secondary_states()

        icon_selector = selector({"icon": {"placeholder": DEFAULT_ICON}})

        all_selectors = {
            CONF_TYPE: self._build_selector_select(
                sorted([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR])
            ),
            CONF_ICON: icon_selector,
            CONF_UPDATE_INTERVAL: self._build_selector_number(),
            CONF_CLEAR_TIMEOUT: self._build_selector_number(),
        }

        if self.show_advanced_options:
            all_selectors[CONF_INCLUDE_ENTITIES] = (
                self._build_selector_entity_simple(self.all_entities, multiple=True),
            )
            all_selectors[CONF_EXCLUDE_ENTITIES] = (
                self._build_selector_entity_simple(
                    self.all_area_entities, multiple=True
                ),
            )
            all_selectors[CONF_ON_STATES] = self._build_selector_select(
                sorted(AVAILABLE_ON_STATES), multiple=True
            )
            all_selectors[CONF_PRESENCE_DEVICE_PLATFORMS] = (
                self._build_selector_select(
                    sorted(ALL_PRESENCE_DEVICE_PLATFORMS), multiple=True
                ),
            )
            all_selectors[CONF_PRESENCE_SENSOR_DEVICE_CLASS] = (
                self._build_selector_select(
                    sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
                ),
            )

        options = OPTIONS_AREA_META if self.area.is_meta() else OPTIONS_AREA
        selectors = {}

        # Apply options for given area type (regular/meta)
        option_keys = [option[0] for option in options]
        for option_key in option_keys:
            selectors[option_key] = all_selectors[option_key]

        data_schema = self._build_options_schema(options=options, selectors=selectors)

        return self.async_show_form(
            step_id="area_config",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_secondary_states(
        self, user_input: dict[str, Any] | None = None
    ):
        """Gather secondary states settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("Validating area secondary states config: %s", user_input)
            AREA_state_schema = SECONDARY_STATES_SCHEMA
            try:
                self.area_options[CONF_SECONDARY_STATES].update(
                    AREA_state_schema(user_input)
                )
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug("Found the following errors: %s", errors)
            except Exception as e:
                _LOGGER.warning("Unexpected error caught: %s", str(e))
            else:
                _LOGGER.debug(
                    "Saving area secondary state config: %s", self.area_options
                )
                return await self.async_step_select_features()

        return self.async_show_form(
            step_id="secondary_states",
            data_schema=self._build_options_schema(
                options=[*(lg.config_flow_options() for lg in ALL_LIGHT_ENTITIES)],
                saved_options=self.config_entry.options.get(CONF_SECONDARY_STATES, {}),
                dynamic_validators={
                    k: v
                    for lg in ALL_LIGHT_ENTITIES
                    for k, v in lg.config_flow_dynamic_validators().items()
                },
                selectors={
                    k: v
                    for lg in ALL_LIGHT_ENTITIES
                    for k, v in lg.config_flow_selectors().items()
                },
            ),
            errors=errors,
        )

    async def async_step_select_features(
        self, user_input: dict[str, Any] | None = None
    ):
        """Ask the user to select features to enable for the area."""
        if user_input is not None:
            self.selected_features = [
                feature for feature, is_selected in user_input.items() if is_selected
            ]

            # Disable feature configuration for meta-areas
            filtered_configurable_features = list(CONFIGURABLE_FEATURES.keys())
            if self.area.is_meta():
                for feature in NON_CONFIGURABLE_FEATURES_META:
                    if feature in filtered_configurable_features:
                        filtered_configurable_features.remove(feature)

            self.features_to_configure = list(
                set(self.selected_features) & set(filtered_configurable_features)
            )
            _LOGGER.debug("Selected features: %s", self.selected_features)
            self.area_options[CONF_ENABLED_FEATURES].update(
                {
                    feature: {}
                    for feature in self.selected_features
                    if feature not in self.features_to_configure
                }
            )
            return await self.async_route_feature_config()

        feature_list = CONF_FEATURE_LIST
        area_type = self.area.config.get(CONF_TYPE)
        if area_type == AREA_TYPE_META:
            feature_list = CONF_FEATURE_LIST_META
        if self.area.id == META_AREA_GLOBAL.lower():
            feature_list = CONF_FEATURE_LIST_GLOBAL

        _LOGGER.debug("Selecting features from %s", feature_list)

        return self.async_show_form(
            step_id="select_features",
            data_schema=self._build_options_schema(
                options=[(feature, False, bool) for feature in feature_list],
                saved_options={
                    feature: (
                        feature
                        in self.config_entry.options.get(CONF_ENABLED_FEATURES, {})
                    )
                    for feature in feature_list
                },
            ),
        )

    async def async_route_feature_config(
        self, _user_input: dict[str, Any] | None = None
    ):
        """Work out next step, if needed.

        Determine the next feature to be configured or finalize the options
        flow if there are no more features left.

           (i.e. all selected features have been configured).
        """
        _LOGGER.debug(
            "Features yet to configure: %s",
            self.features_to_configure,
        )
        _LOGGER.debug("Current config is: %s", self.area_options)
        if self.features_to_configure:
            current_feature = self.features_to_configure.pop()
            _LOGGER.debug(
                "Initiating configuration step for feature %s", current_feature
            )
            feature_conf_step = getattr(
                self, f"async_step_feature_conf_{current_feature}"
            )
            return await feature_conf_step()
        _LOGGER.debug("All features configured, saving config: %s", self.area_options)
        return self.async_create_entry(title="", data=self.area_options)

    async def async_step_feature_conf_advanced_light_groups(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure the advanced light groups bits."""

        return await self.do_feature_config(
            name=CONF_FEATURE_ADVANCED_LIGHT_GROUPS,
            options=[
                *([lg.advanced_config_flow_schema() for lg in ALL_LIGHT_ENTITIES])
            ],
            dynamic_validators={
                k: v
                for lg in ALL_LIGHT_ENTITIES
                for k, v in lg.advanced_config_flow_dynamic_validators().items()
            },
            selectors={
                k: v
                for lg in ALL_LIGHT_ENTITIES
                for k, v in lg.advanced_config_flow_selectors().items()
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_climate_groups(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure the climate groups feature."""

        available_states = [
            AreaState.AREA_STATE_OCCUPIED,
            AreaState.AREA_STATE_EXTENDED,
        ]

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

    async def async_step_feature_conf_area_aware_media_player(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure the area aware media player feature."""

        available_states = [
            AreaState.AREA_STATE_OCCUPIED,
            AreaState.AREA_STATE_EXTENDED,
            AreaState.AREA_STATE_SLEEP,
        ]

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

    async def async_step_feature_conf_aggregates(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure the sensor aggregates feature."""

        selectors = {
            CONF_AGGREGATES_MIN_ENTITIES: self._build_selector_number(
                unit_of_measurement="entities"
            )
        }

        return await self.do_feature_config(
            name=CONF_FEATURE_AGGREGATION,
            options=OPTIONS_AGGREGATES,
            selectors=selectors,
            user_input=user_input,
        )

    async def async_step_feature_conf_presence_hold(
        self, user_input: dict[str, Any] | None = None
    ):
        """Configure the sensor presence_hold feature."""

        selectors = {CONF_PRESENCE_HOLD_TIMEOUT: self._build_selector_number()}

        return await self.do_feature_config(
            name=CONF_FEATURE_PRESENCE_HOLD,
            options=OPTIONS_PRESENCE_HOLD,
            selectors=selectors,
            user_input=user_input,
        )

    async def do_feature_config(
        self,
        name: str,
        options: dict[str, Any],
        dynamic_validators: dict[str, Any] | None = None,
        selectors: dict[str, Selector] | None = None,
        user_input: dict[str, Any] | None = None,
    ):
        """Execute step for a generic feature."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug("Validating %s feature config: %s", name, user_input)
            try:
                validated_input = CONFIGURABLE_FEATURES[name](user_input)
            except vol.MultipleInvalid as validation:
                errors = {
                    error.path[0]: "malformed_input" for error in validation.errors
                }
                _LOGGER.debug("Found the following errors: %s", errors)
            else:
                _LOGGER.debug("Saving %s feature config: %s", name, validated_input)
                self.area_options[CONF_ENABLED_FEATURES][name] = validated_input
                return await self.async_route_feature_config()

        _LOGGER.debug("Config entry options: %s", self.config_entry.options)

        saved_options = self.config_entry.options.get(CONF_ENABLED_FEATURES, {})

        # Handle legacy options somewhat-gracefully
        # @REMOVEME on 4.x.x, users shall be updated by then
        if not isinstance(saved_options, dict):
            saved_options = {}

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
