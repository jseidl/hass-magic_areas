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

from .base.config import ConfigOptionSelector
from .const import (
    ADDITIONAL_LIGHT_TRACKING_ENTITIES,
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    ALL_SENSOR_DEVICE_CLASSES,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONFIGURABLE_AREA_STATE_MAP,
    DISTRESS_SENSOR_CLASSES,
    DOMAIN,
    AggregatesOptionKey,
    AggregatesOptionSet,
    AreaAwareMediaPlayerOptionKey,
    AreaAwareMediaPlayerOptionSet,
    AreaEventType,
    AreaHealthOptionKey,
    AreaHealthOptionSet,
    AreaInfoOptionKey,
    AreaInfoOptionSet,
    AreaState,
    AreaStateGroups,
    AreaType,
    ClimateGroupOptionKey,
    ClimateGroupOptionSet,
    EntityFilters,
    LightGroupOptionKey,
    LightGroupOptionSet,
    MagicAreasConfig,
    MagicAreasDataKey,
    MagicConfigEntryVersion,
    MetaAreaType,
    PresenceHoldOptionKey,
    PresenceHoldOptionSet,
    SecondaryStatesOptionKey,
    SecondaryStatesOptionSet,
)
from .util import basic_area_from_floor, basic_area_from_meta, basic_area_from_object

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class ConfigBase:
    """Base class for config flow."""

    config_entry = None

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
            config_entry = MagicAreasConfig(area_object)

            # Handle Meta area
            if area_object.is_meta:
                _LOGGER.debug(
                    "ConfigFlow: Meta area %s found, setting correct type.",
                    area_object.id,
                )
                config_entry.get(AreaInfoOptionSet.key).load(
                    {AreaInfoOptionKey.TYPE: AreaType.META}
                )

            return self.async_create_entry(
                title=area_object.name, data=config_entry.get_schema()
            )

        # Filter out already-configured areas
        configured_areas = []
        ma_data = self.hass.data.get(MagicAreasDataKey.MODULE_DATA, {})

        for config_data in ma_data.values():
            configured_areas.append(config_data[MagicAreasDataKey.AREA].id)

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
        self.config = MagicAreasConfig(
            config_entry.runtime_data.area, config_object=config_entry
        )
        self.entity_helpers = {
            "all_entities": [],
            "area_entities": [],
            "all_area_entities": [],
            "all_lights": [],
            "all_media_players": [],
            "all_binary_entities": [],
            "all_light_tracking_entities": [],
        }

    def _get_feature_list(self) -> list[str]:
        """Return list of available features for area type."""

        feature_list = CONF_FEATURE_LIST
        area_type = (
            self.config.get(AreaInfoOptionSet.key).get(AreaInfoOptionKey.TYPE).value()
        )
        if area_type == AreaType.META:
            feature_list = CONF_FEATURE_LIST_META
        if self.area.id == MetaAreaType.GLOBAL:
            feature_list = CONF_FEATURE_LIST_GLOBAL

        return feature_list

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(title="", data=dict(self.config.get_values()))

    async def async_step_init(self, user_input=None):
        """Initialize the options flow."""

        self.data = self.hass.data[MagicAreasDataKey.MODULE_DATA][
            self.config_entry.entry_id
        ]
        self.area = self.data[MagicAreasDataKey.AREA]

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
                if entity_id.split(".")[0] in EntityFilters.extended
            )
        )

        # Return all relevant area entities that exists
        # in self.all_entities
        filtered_area_entities = []
        for domain in EntityFilters.extended:
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
                if entity_id.split(".")[0] in EntityFilters.binary
            )
        )

        self.all_area_entities = sorted(
            self.area_entities
            + self.config.get(AreaInfoOptionSet.key)
            .get(AreaInfoOptionKey.EXCLUDE_ENTITIES)
            .value()
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

        _LOGGER.debug(
            "%s: Loaded area options: %s",
            self.area.name,
            str(self.config.get_schema(raw=True)),
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
        for feature in self.config.get_enabled_features():
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
                self.config.get(AreaInfoOptionSet.key).load(user_input)
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
                    str(self.config.get(AreaInfoOptionSet.key).get_values()),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            AreaInfoOptionKey.TYPE: ConfigOptionSelector.select(
                sorted([AreaType.INTERIOR, AreaType.EXTERIOR])
            ),
            AreaInfoOptionKey.INCLUDE_ENTITIES: ConfigOptionSelector.entity(
                self.all_entities, multiple=True
            ),
            AreaInfoOptionKey.EXCLUDE_ENTITIES: ConfigOptionSelector.entity(
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
            options=options,
            saved_options=self.config.get(AreaInfoOptionSet.key).get_values(),
            selectors=selectors,
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
                self.config.get(AreaInfoOptionSet.key).load(user_input)
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
                    str(self.config.get(AreaInfoOptionSet.key).get_values()),
                )

                return await self.async_step_show_menu()

        all_selectors = {
            AreaInfoOptionKey.PRESENCE_SENSOR_DOMAINS: ConfigOptionSelector.select(
                sorted(EntityFilters.presence), multiple=True
            ),
            AreaInfoOptionKey.PRESENCE_SENSOR_DEVICE_CLASSES: ConfigOptionSelector.select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            AreaInfoOptionKey.UPDATE_INTERVAL: ConfigOptionSelector.number(
                unit_of_measurement="seconds"
            ),
            AreaInfoOptionKey.CLEAR_TIMEOUT: ConfigOptionSelector.number(
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
            options=options,
            saved_options=self.config.get(AreaInfoOptionSet.key).get_values(),
            selectors=selectors,
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
            try:
                self.config.get(SecondaryStatesOptionSet.key).load(user_input)
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
                    str(self.config.get(SecondaryStatesOptionSet.key).get_values()),
                )
                return await self.async_step_show_menu()

        return self.async_show_form(
            step_id="secondary_states",
            data_schema=self._build_options_schema(
                options=self.config.get(
                    SecondaryStatesOptionSet.key
                ).generate_options(),
                saved_options=self.config.get(
                    SecondaryStatesOptionSet.key
                ).get_values(),
                dynamic_validators={
                    SecondaryStatesOptionKey.AREA_LIGHT_SENSOR: vol.In(
                        EMPTY_ENTRY + self.all_light_tracking_entities
                    ),
                    SecondaryStatesOptionKey.SLEEP_ENTITY: vol.In(
                        EMPTY_ENTRY + self.all_binary_entities
                    ),
                    SecondaryStatesOptionKey.ACCENT_ENTITY: vol.In(
                        EMPTY_ENTRY + self.all_binary_entities
                    ),
                },
                selectors={
                    SecondaryStatesOptionKey.AREA_LIGHT_SENSOR: ConfigOptionSelector.entity(
                        self.all_light_tracking_entities
                    ),
                    SecondaryStatesOptionKey.SLEEP_ENTITY: ConfigOptionSelector.entity(
                        self.all_binary_entities
                    ),
                    SecondaryStatesOptionKey.ACCENT_ENTITY: ConfigOptionSelector.entity(
                        self.all_binary_entities
                    ),
                    SecondaryStatesOptionKey.SLEEP_TIMEOUT: ConfigOptionSelector.number(
                        unit_of_measurement="minutes"
                    ),
                    SecondaryStatesOptionKey.EXTENDED_TIME: ConfigOptionSelector.number(
                        unit_of_measurement="minutes"
                    ),
                    SecondaryStatesOptionKey.EXTENDED_TIMEOUT: ConfigOptionSelector.number(
                        unit_of_measurement="minutes"
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_select_features(self, user_input=None):
        """Ask the user to select features to enable for the area."""

        feature_list = self.config.get_available_features()

        if user_input is not None:
            selected_features = [
                feature for feature, is_selected in user_input.items() if is_selected
            ]

            _LOGGER.debug(
                "OptionsFlow: Selected features for area %s: %s",
                self.area.name,
                str(selected_features),
            )

            for feature in feature_list:
                self.config.get(feature).active = feature in selected_features

            return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Selecting features for area %s from %s",
            self.area.name,
            feature_list,
        )

        enabled_features = self.config.get_enabled_features()

        return self.async_show_form(
            step_id="select_features",
            data_schema=self._build_options_schema(
                options=[(feature, False, bool) for feature in feature_list],
                saved_options={
                    feature: (feature in enabled_features) for feature in feature_list
                },
            ),
        )

    async def async_step_finish(self, user_input=None):
        """Save options and exit options flow."""
        _LOGGER.debug(
            "OptionsFlow: All features configured for area %s, saving config: %s",
            self.area.name,
            str(self.config.get_values()),
        )
        return await self._update_options()

    async def async_step_feature_conf_light_groups(self, user_input=None):
        """Configure the light groups feature."""

        available_states = AreaStateGroups.builtin.copy()

        light_group_state_exempt = [AreaState.DARK]
        for extra_state, extra_state_entity in CONFIGURABLE_AREA_STATE_MAP.items():
            # Skip AREA_STATE_DARK because lights can't be tied to this state
            if extra_state in light_group_state_exempt:
                continue

            if (
                self.config.get(SecondaryStatesOptionSet.key)
                .get(extra_state_entity)
                .value()
            ):
                available_states.append(extra_state)

        light_group_act_on_options = [AreaEventType.OCCUPANCY, AreaEventType.STATE]

        return await self.do_feature_config(
            name=LightGroupOptionSet.key,
            options=self.config.get(LightGroupOptionSet.key).generate_options(),
            dynamic_validators={
                LightGroupOptionKey.OVERHEAD_LIGHTS: cv.multi_select(self.all_lights),
                LightGroupOptionKey.OVERHEAD_LIGHTS_STATES: cv.multi_select(
                    available_states
                ),
                LightGroupOptionKey.OVERHEAD_LIGHTS_CONTROL_ON: cv.multi_select(
                    light_group_act_on_options
                ),
                LightGroupOptionKey.SLEEP_LIGHTS: cv.multi_select(self.all_lights),
                LightGroupOptionKey.SLEEP_LIGHTS_STATES: cv.multi_select(
                    available_states
                ),
                LightGroupOptionKey.SLEEP_LIGHTS_CONTROL_ON: cv.multi_select(
                    light_group_act_on_options
                ),
                LightGroupOptionKey.ACCENT_LIGHTS: cv.multi_select(self.all_lights),
                LightGroupOptionKey.ACCENT_LIGHTS_STATES: cv.multi_select(
                    available_states
                ),
                LightGroupOptionKey.ACCENT_LIGHTS_CONTROL_ON: cv.multi_select(
                    light_group_act_on_options
                ),
                LightGroupOptionKey.TASK_LIGHTS: cv.multi_select(self.all_lights),
                LightGroupOptionKey.TASK_LIGHTS_STATES: cv.multi_select(
                    available_states
                ),
                LightGroupOptionKey.TASK_LIGHTS_CONTROL_ON: cv.multi_select(
                    light_group_act_on_options
                ),
            },
            selectors={
                LightGroupOptionKey.OVERHEAD_LIGHTS: ConfigOptionSelector.entity(
                    self.all_lights, multiple=True
                ),
                LightGroupOptionKey.OVERHEAD_LIGHTS_STATES: ConfigOptionSelector.select(
                    available_states, multiple=True
                ),
                LightGroupOptionKey.OVERHEAD_LIGHTS_CONTROL_ON: ConfigOptionSelector.select(
                    light_group_act_on_options, multiple=True
                ),
                LightGroupOptionKey.SLEEP_LIGHTS: ConfigOptionSelector.entity(
                    self.all_lights, multiple=True
                ),
                LightGroupOptionKey.SLEEP_LIGHTS_STATES: ConfigOptionSelector.select(
                    available_states, multiple=True
                ),
                LightGroupOptionKey.SLEEP_LIGHTS_CONTROL_ON: ConfigOptionSelector.select(
                    light_group_act_on_options, multiple=True
                ),
                LightGroupOptionKey.ACCENT_LIGHTS: ConfigOptionSelector.entity(
                    self.all_lights, multiple=True
                ),
                LightGroupOptionKey.ACCENT_LIGHTS_STATES: ConfigOptionSelector.select(
                    available_states, multiple=True
                ),
                LightGroupOptionKey.ACCENT_LIGHTS_CONTROL_ON: ConfigOptionSelector.select(
                    light_group_act_on_options, multiple=True
                ),
                LightGroupOptionKey.TASK_LIGHTS: ConfigOptionSelector.entity(
                    self.all_lights, multiple=True
                ),
                LightGroupOptionKey.TASK_LIGHTS_STATES: ConfigOptionSelector.select(
                    available_states, multiple=True
                ),
                LightGroupOptionKey.TASK_LIGHTS_CONTROL_ON: ConfigOptionSelector.select(
                    light_group_act_on_options, multiple=True
                ),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_climate_groups(self, user_input=None):
        """Configure the climate groups feature."""

        available_states = [AreaState.OCCUPIED, AreaState.EXTENDED]

        return await self.do_feature_config(
            name=ClimateGroupOptionSet.key,
            options=(
                OPTIONS_CLIMATE_GROUP
                if not self.area.is_meta()
                else OPTIONS_CLIMATE_GROUP_META
            ),
            dynamic_validators={
                ClimateGroupOptionKey.TURN_ON_STATE: vol.In(
                    EMPTY_ENTRY + available_states
                ),
            },
            selectors={
                ClimateGroupOptionKey.TURN_ON_STATE: ConfigOptionSelector.select(
                    EMPTY_ENTRY + available_states
                )
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_health(self, user_input=None):
        """Configure the climate groups feature."""

        return await self.do_feature_config(
            name=AreaHealthOptionSet.key,
            options=self.config.get(AreaHealthOptionSet.key).generate_options(),
            dynamic_validators={
                AreaHealthOptionKey.DEVICE_CLASSES: vol.In(
                    EMPTY_ENTRY + DISTRESS_SENSOR_CLASSES
                ),
            },
            selectors={
                AreaHealthOptionKey.DEVICE_CLASSES: ConfigOptionSelector.select(
                    EMPTY_ENTRY + DISTRESS_SENSOR_CLASSES, multiple=True
                )
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_area_aware_media_player(self, user_input=None):
        """Configure the area aware media player feature."""

        available_states = [AreaState.OCCUPIED, AreaState.EXTENDED, AreaState.SLEEP]

        return await self.do_feature_config(
            name=AreaAwareMediaPlayerOptionSet.key,
            options=self.config.get(AreaAwareMediaPlayerOptionSet).generate_options(),
            dynamic_validators={
                AreaAwareMediaPlayerOptionKey.NOTIFICATION_DEVICES: cv.multi_select(
                    self.all_media_players
                ),
                AreaAwareMediaPlayerOptionKey.NOTIFY_STATES: cv.multi_select(
                    available_states
                ),
            },
            selectors={
                AreaAwareMediaPlayerOptionKey.NOTIFICATION_DEVICES: ConfigOptionSelector.entity(
                    self.all_media_players, multiple=True
                ),
                AreaAwareMediaPlayerOptionKey.NOTIFY_STATES: ConfigOptionSelector.select(
                    available_states, multiple=True
                ),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_aggregates(self, user_input=None):
        """Configure the sensor aggregates feature."""

        selectors = {
            AggregatesOptionKey.MIN_ENTITIES: ConfigOptionSelector.number(
                unit_of_measurement="entities"
            ),
            AggregatesOptionKey.BINARY_SENSOR_DEVICE_CLASSES: ConfigOptionSelector.select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            AggregatesOptionKey.SENSOR_DEVICE_CLASSES: ConfigOptionSelector.select(
                sorted(ALL_SENSOR_DEVICE_CLASSES), multiple=True
            ),
            AggregatesOptionKey.ILLUMINANCE_THRESHOLD: ConfigOptionSelector.number(
                unit_of_measurement="lx", mode="slider", min_value=0, max_value=1000
            ),
        }

        return await self.do_feature_config(
            name=AggregatesOptionSet.key,
            options=self.config.get(AggregatesOptionSet).generate_options(),
            selectors=selectors,
            user_input=user_input,
        )

    async def async_step_feature_conf_presence_hold(self, user_input=None):
        """Configure the sensor presence_hold feature."""

        selectors = {
            PresenceHoldOptionKey.TIMEOUT: ConfigOptionSelector.number(
                min_value=0, unit_of_measurement="minutes"
            )
        }

        return await self.do_feature_config(
            name=PresenceHoldOptionSet.key,
            options=self.config.get(PresenceHoldOptionSet).generate_options(),
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
                self.config.get(name).load(user_input)
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
                    str(self.config.get(name).get_values()),
                )
                return await self.async_step_show_menu()

        _LOGGER.debug(
            "OptionsFlow: Config entry options for area %s: %s",
            self.area.name,
            str(self.config_entry.options),
        )

        return self.async_show_form(
            step_id=f"feature_conf_{name}",
            data_schema=self._build_options_schema(
                options=options,
                saved_options=self.config.get(name).get_values(),
                dynamic_validators=dynamic_validators,
                selectors=selectors,
            ),
            errors=errors,
        )
