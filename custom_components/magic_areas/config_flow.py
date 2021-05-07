import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    ALL_BINARY_SENSOR_DEVICE_CLASSES,
    AREA_TYPE_META,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_FEATURE_LIGHT_GROUPS,
    CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
    CONF_FEATURE_AGGREGATION,
    CONF_INCLUDE_ENTITIES,
    CONF_MAIN_LIGHTS,
    CONF_NIGHT_ENTITY,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_LIGHTS,
    CONF_TYPE,
    CONFIGURABLE_FEATURES,
    DATA_AREA_OBJECT,
    DOMAIN,
    META_AREA_GLOBAL,
    META_AREA_SCHEMA,
    MODULE_DATA,
    OPTIONS_AREA,
    OPTIONS_AREA_META,
    OPTIONS_LIGHT_GROUP,
    OPTIONS_AGGREGATES,
    OPTIONS_AREA_AWARE_MEDIA_PLAYER,
    REGULAR_AREA_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

EMPTY_ENTRY = [""]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Lighting."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_abort(reason="not_supported")

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        await self.async_set_unique_id(user_input[CONF_NAME])
        for entry in self._async_current_entries():
            if entry.unique_id == self.unique_id:
                self.hass.config_entries.async_update_entry(entry, data=user_input)
                self._abort_if_unique_id_configured()
        return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle a option flow for Adaptive Lighting."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self.data = None
        self.area = None
        self.all_entities = []
        self.all_lights = []
        self.all_media_players = []
        self.selected_features = []
        self.features_to_configure = None

    def _build_options_schema(self, options, old_options=None, dynamic_validators={}):
        _LOGGER.debug(
            f"Building schema from options: {options} - dynamic_validators: {dynamic_validators}"
        )
        if old_options is None:
            old_options = self.config_entry.options
        _LOGGER.debug(f"Data for pre-populating fields: {old_options}")
        schema = vol.Schema(
            {
                vol.Optional(
                    name,
                    description={"suggested_value": old_options.get(name)},
                    default=default,
                ): dynamic_validators.get(name, validation)
                for name, default, validation in options
            }
        )
        _LOGGER.debug(f"Built schema: {schema}")
        return schema

    async def async_step_init(self, user_input=None):
        """Initialize the options flow"""
        self.data = self.hass.data[MODULE_DATA][self.config_entry.entry_id]
        self.area = self.data[DATA_AREA_OBJECT]

        _LOGGER.debug(f"Initializing options flow for area {self.area.name}")
        _LOGGER.debug(f"Old options in config entry: {self.config_entry.options}")

        self.all_entities = sorted(self.hass.states.async_entity_ids())
        self.all_lights = sorted(
            entity["entity_id"] for entity in self.area.entities.get(LIGHT_DOMAIN, [])
        )
        self.all_media_players = sorted(
            entity["entity_id"]
            for entity in self.area.entities.get(MEDIA_PLAYER_DOMAIN, [])
        )

        return await self.async_step_area_config()

    async def async_step_area_config(self, user_input=None):
        """Gather basic settings for the area."""
        errors = {}
        if user_input is not None:
            _LOGGER.debug(f"Validating area base config: {user_input}")
            area_schema = (
                META_AREA_SCHEMA
                if self.area.config.get(CONF_TYPE) == AREA_TYPE_META
                else REGULAR_AREA_SCHEMA
            )
            try:
                self.area_options = area_schema(user_input)
            except vol.MultipleInvalid as validation:
                errors = {error.path[0]: error.msg for error in validation.errors}
                _LOGGER.debug(f"Found the following errors: {errors}")
            else:
                _LOGGER.debug(f"Saving area base config: {self.area_options}")
                return await self.async_step_select_features()

        return self.async_show_form(
            step_id="area_config",
            data_schema=self._build_options_schema(
                options=(
                    OPTIONS_AREA_META
                    if self.area.config.get(CONF_TYPE) == AREA_TYPE_META
                    else OPTIONS_AREA
                ),
                dynamic_validators={
                    CONF_INCLUDE_ENTITIES: cv.multi_select(self.all_entities),
                    CONF_EXCLUDE_ENTITIES: cv.multi_select(self.all_entities),
                    CONF_PRESENCE_SENSOR_DEVICE_CLASS: cv.multi_select(
                        sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES)
                    ),
                },
            ),
            errors=errors,
        )

    async def async_step_select_features(self, user_input=None):
        """Ask the user to select features to enable for the area."""
        if user_input is not None:
            self.selected_features = [
                feature for feature, is_selected in user_input.items() if is_selected
            ]
            self.features_to_configure = list(
                set(self.selected_features) & set(CONFIGURABLE_FEATURES.keys())
            )
            _LOGGER.debug(f"Selected features: {self.selected_features}")
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

        _LOGGER.debug(f"Selecting features from {feature_list}")

        return self.async_show_form(
            step_id="select_features",
            data_schema=self._build_options_schema(
                options=[(feature, False, bool) for feature in feature_list],
                old_options={
                    feature: (
                        feature
                        in self.config_entry.options.get(CONF_ENABLED_FEATURES, {})
                    )
                    for feature in feature_list
                },
            ),
        )

    async def async_route_feature_config(self, user_input=None):
        """Determine the next feature to be configured or finalize the options
        flow if there are no more features left (i.e. all selected features have
        been configured)."""
        _LOGGER.debug(f"Features yet to configure: {self.features_to_configure}")
        _LOGGER.debug(f"Current config is: {self.area_options}")
        if self.features_to_configure:
            current_feature = self.features_to_configure.pop()
            _LOGGER.debug(
                f"Initiating configuration step for feature {current_feature}"
            )
            feature_conf_step = getattr(
                self, f"async_step_feature_conf_{current_feature}"
            )
            return await feature_conf_step()
        else:
            _LOGGER.debug(
                f"All features configured, saving config: {self.area_options}"
            )
            return self.async_create_entry(title="", data=self.area_options)

    async def async_step_feature_conf_light_groups(self, user_input=None):
        """Configure the light groups feature"""
        return await self.do_feature_config(
            name=CONF_FEATURE_LIGHT_GROUPS,
            options=OPTIONS_LIGHT_GROUP,
            dynamic_validators={
                CONF_MAIN_LIGHTS: cv.multi_select(self.all_lights),
                CONF_SLEEP_LIGHTS: cv.multi_select(self.all_lights),
                CONF_NIGHT_ENTITY: vol.In(EMPTY_ENTRY + self.all_entities),
                CONF_SLEEP_ENTITY: vol.In(EMPTY_ENTRY + self.all_entities),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_area_aware_media_player(self, user_input=None):
        """Configure the area aware media player feature"""
        return await self.do_feature_config(
            name=CONF_FEATURE_AREA_AWARE_MEDIA_PLAYER,
            options=OPTIONS_AREA_AWARE_MEDIA_PLAYER,
            dynamic_validators={
                CONF_NOTIFICATION_DEVICES: cv.multi_select(self.all_media_players),
            },
            user_input=user_input,
        )

    async def async_step_feature_conf_aggregates(self, user_input=None):
        """Configure the sensor aggregates feature"""
        return await self.do_feature_config(
            name=CONF_FEATURE_AGGREGATION,
            options=OPTIONS_AGGREGATES,
            user_input=user_input,
        )

    async def do_feature_config(
        self, name, options, dynamic_validators={}, user_input=None
    ):
        """Execute step for a generic feature"""
        errors = {}
        if user_input is not None:
            _LOGGER.debug(f"Validating {name} feature config: {user_input}")
            try:
                validated_input = CONFIGURABLE_FEATURES[name](user_input)
            except vol.MultipleInvalid as validation:
                errors = {
                    error.path[0]: "malformed_input" for error in validation.errors
                }
                _LOGGER.debug(f"Found the following errors: {errors}")
            else:
                _LOGGER.debug(f"Saving {name} feature config: {validated_input}")
                self.area_options[CONF_ENABLED_FEATURES][name] = validated_input
                return await self.async_route_feature_config()

        return self.async_show_form(
            step_id=f"feature_conf_{name}",
            data_schema=self._build_options_schema(
                options=options,
                old_options=self.config_entry.options.get(
                    CONF_ENABLED_FEATURES, {}
                ).get(name, {}),
                dynamic_validators=dynamic_validators,
            ),
            errors=errors,
        )
