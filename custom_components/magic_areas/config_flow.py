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
    AREA_TYPE_EXTERIOR,
    AREA_TYPE_INTERIOR,
    AREA_TYPE_META,
    CONF_ENABLED_FEATURES,
    CONF_EXCLUDE_ENTITIES,
    CONF_FEATURE_LIST,
    CONF_FEATURE_LIST_GLOBAL,
    CONF_FEATURE_LIST_META,
    CONF_INCLUDE_ENTITIES,
    CONF_MAIN_LIGHTS,
    CONF_NIGHT_ENTITY,
    CONF_NOTIFICATION_DEVICES,
    CONF_PRESENCE_SENSOR_DEVICE_CLASS,
    CONF_SLEEP_ENTITY,
    CONF_SLEEP_LIGHTS,
    CONF_TYPE,
    DATA_AREA_OBJECT,
    DOMAIN,
    META_AREA_GLOBAL,
    MODULE_DATA,
    VALIDATION_TUPLES,
    VALIDATION_TUPLES_META,
)

_LOGGER = logging.getLogger(__name__)


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

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        conf = self.config_entry
        if conf.source == config_entries.SOURCE_IMPORT:
            return self.async_show_form(step_id="init", data_schema=None)
        errors = {}

        if user_input is not None:
            # validate_options(user_input, errors)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        # Fetch area entities
        data = self.hass.data[MODULE_DATA][self.config_entry.entry_id]
        area = data[DATA_AREA_OBJECT]
        area_type = area.config.get(CONF_TYPE)

        feature_list = CONF_FEATURE_LIST

        _VALIDATION_TUPLES = VALIDATION_TUPLES

        if area_type == AREA_TYPE_META:
            _VALIDATION_TUPLES = VALIDATION_TUPLES_META
            feature_list = CONF_FEATURE_LIST_META

        if area.id == META_AREA_GLOBAL.lower():
            feature_list = CONF_FEATURE_LIST_GLOBAL

        all_lights = (
            [light["entity_id"] for light in area.entities[LIGHT_DOMAIN]]
            if LIGHT_DOMAIN in area.entities.keys()
            else []
        )
        all_media_players = (
            [
                media_player["entity_id"]
                for media_player in area.entities[MEDIA_PLAYER_DOMAIN]
            ]
            if MEDIA_PLAYER_DOMAIN in area.entities.keys()
            else []
        )
        all_entities = [entity for entity in self.hass.states.async_entity_ids()]
        entity_list = cv.multi_select(sorted(all_entities))
        empty_entry = [""]
        to_replace = {
            CONF_INCLUDE_ENTITIES: entity_list,
            CONF_EXCLUDE_ENTITIES: entity_list,
            CONF_ENABLED_FEATURES: cv.multi_select(sorted(feature_list)),
            CONF_PRESENCE_SENSOR_DEVICE_CLASS: cv.multi_select(
                sorted(ALL_BINARY_SENSOR_DEVICE_CLASSES)
            ),
            CONF_NOTIFICATION_DEVICES: cv.multi_select(sorted(all_media_players)),
            CONF_MAIN_LIGHTS: cv.multi_select(sorted(all_lights)),
            CONF_SLEEP_LIGHTS: cv.multi_select(sorted(all_lights)),
            CONF_NIGHT_ENTITY: vol.In(sorted(empty_entry + all_entities)),
            CONF_SLEEP_ENTITY: vol.In(sorted(empty_entry + all_entities)),
            CONF_TYPE: vol.In(sorted([AREA_TYPE_INTERIOR, AREA_TYPE_EXTERIOR])),
        }

        options_schema = {}
        for name, default, validation in _VALIDATION_TUPLES:
            key = vol.Optional(name, default=conf.options.get(name, default))
            value = to_replace.get(name, validation)
            options_schema[key] = value

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(options_schema), errors=errors
        )
