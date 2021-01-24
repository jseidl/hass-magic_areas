import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN

import homeassistant.helpers.config_validation as cv

from .const import (
    MODULE_DATA, 
    DATA_AREA_OBJECT, 
    DOMAIN, 
    _AREA_SCHEMA, 
    VALIDATION_TUPLES, 
    CONF_INCLUDE_ENTITIES, 
    CONF_EXCLUDE_ENTITIES, 
    CONF_PRESENCE_SENSOR_DEVICE_CLASS, 
    CONF_ENABLED_FEATURES, 
    CONF_FEATURE_LIST, 
    CONF_MAIN_LIGHTS,
    CONF_SLEEP_LIGHTS,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_STATE,
    CONF_SLEEP_TIMEOUT,
    CONF_NIGHT_ENTITY,
    CONF_NIGHT_STATE,
    ALL_BINARY_SENSOR_DEVICE_CLASSES
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Lighting."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        area_registry = await self.hass.helpers.area_registry.async_get_registry()
        areas = area_registry.async_list_areas()

        area_names = [area.name for area in areas]

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME): vol.In(area_names)}),
            #data_schema=_AREA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        await self.async_set_unique_id(user_input[CONF_NAME])
        _LOGGER.warning(f"-- MARK -- {self._async_current_entries()}")
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

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        errors = {}

        if user_input is not None:
            #validate_options(user_input, errors)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Fetch area entities
        data = self.hass.data[MODULE_DATA][self.config_entry.entry_id]
        area = data[DATA_AREA_OBJECT]

        all_lights = [
            light['entity_id']
            for light in area.entities[LIGHT_DOMAIN]
        ] if LIGHT_DOMAIN in area.entities.keys() else []
        all_entities = [
            entity
            for entity in self.hass.states.async_entity_ids()
        ]
        entity_list = cv.multi_select(sorted(all_entities))
        empty_entry = [""]
        to_replace = {
            CONF_INCLUDE_ENTITIES: entity_list,
            CONF_EXCLUDE_ENTITIES: entity_list,
            CONF_ENABLED_FEATURES: cv.multi_select(sorted(CONF_FEATURE_LIST)),
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: cv.multi_select(sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES)),
            CONF_MAIN_LIGHTS: cv.multi_select(sorted(all_lights)),
            CONF_SLEEP_LIGHTS: cv.multi_select(sorted(all_lights)),
            CONF_NIGHT_ENTITY: vol.In(sorted(empty_entry+all_entities)),
            CONF_SLEEP_ENTITY: vol.In(sorted(empty_entry+all_entities))
            }

        options_schema = {}
        for name, default, validation in VALIDATION_TUPLES:
            key = vol.Optional(name, default=conf.options.get(name, default))
            value = to_replace.get(name, validation)
            options_schema[key] = value 

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(options_schema), errors=errors
        )