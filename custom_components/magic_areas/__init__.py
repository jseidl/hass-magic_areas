"""Magic Areas component for Home Assistant."""

from collections import defaultdict
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as areareg_async_get
from homeassistant.helpers.floor_registry import async_get as floorreg_async_get

from .base.magic import MagicArea, MagicMetaArea
from .const import (
    CONF_CLEAR_TIMEOUT,
    CONF_EXTENDED_TIME,
    CONF_EXTENDED_TIMEOUT,
    CONF_ID,
    CONF_NAME,
    CONF_SECONDARY_STATES,
    CONF_SLEEP_TIMEOUT,
    DATA_AREA_OBJECT,
    DATA_UNDO_UPDATE_LISTENER,
    DEFAULT_CLEAR_TIMEOUT,
    DEFAULT_EXTENDED_TIME,
    DEFAULT_EXTENDED_TIMEOUT,
    DEFAULT_SLEEP_TIMEOUT,
    META_AREA_EXTERIOR,
    META_AREA_GLOBAL,
    META_AREA_INTERIOR,
    MODULE_DATA,
    MagicConfigEntryVersion,
    MetaAreaType,
)
from .util import (
    basic_area_from_floor,
    basic_area_from_meta,
    basic_area_from_object,
    seconds_to_minutes,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the component."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""
    data = hass.data.setdefault(MODULE_DATA, {})
    area_id = config_entry.data[CONF_ID]
    area_name = config_entry.data[CONF_NAME]

    _LOGGER.debug("%s: Setting up entry.", area_name)

    # Load floors
    floor_registry = floorreg_async_get(hass)
    floors = floor_registry.async_list_floors()

    non_floor_meta_ids = [
        meta_area_type
        for meta_area_type in MetaAreaType
        if meta_area_type != MetaAreaType.FLOOR
    ]
    floor_ids = [f.floor_id for f in floors]

    if area_id in non_floor_meta_ids:
        meta_area = basic_area_from_meta(area_id)
        magic_area = MagicMetaArea(hass, meta_area, config_entry)
    elif area_id in floor_ids:
        meta_area = basic_area_from_floor(floor_registry.async_get_floor(area_id))
        magic_area = MagicMetaArea(hass, meta_area, config_entry)
    else:
        area_registry = areareg_async_get(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.warning("%s: ID '%s' not found on registry", area_name, area_id)
            return False

        _LOGGER.debug("%s: Got area from registry: %s", area_name, str(area))

        magic_area = MagicArea(
            hass,
            basic_area_from_object(area),
            config_entry,
        )

    _LOGGER.debug(
        "%s: Magic Area (%s) created: %s",
        magic_area.name,
        magic_area.id,
        str(magic_area.config),
    )

    undo_listener = config_entry.add_update_listener(async_update_options)

    data[config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(
        config_entry, magic_area.available_platforms()
    )

    # Conditional reload of related meta-areas
    # Populate dict with all meta-areas with ID as key
    meta_areas = defaultdict()

    for area in data.values():
        area_obj = area[DATA_AREA_OBJECT]
        if area_obj.is_meta():
            meta_areas[area_obj.id] = area_obj

    # Handle non-meta areas
    if not magic_area.is_meta():
        meta_area_key = (
            META_AREA_EXTERIOR.lower()
            if magic_area.is_exterior()
            else META_AREA_INTERIOR.lower()
        )

        if meta_area_key in meta_areas:
            meta_area_object = meta_areas[meta_area_key]

            if meta_area_object.initialized:
                await hass.config_entries.async_reload(
                    meta_area_object.hass_config.entry_id
                )
    else:
        meta_area_global_id = META_AREA_GLOBAL.lower()

        if magic_area.id != meta_area_global_id and meta_area_global_id in meta_areas:
            if meta_areas[meta_area_global_id].initialized:
                await hass.config_entries.async_reload(
                    meta_areas[meta_area_global_id].hass_config.entry_id
                )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug(
        "Detected options change for entry %s, reloading", config_entry.entry_id
    )
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    data = hass.data[MODULE_DATA]
    area_data = data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    await hass.config_entries.async_unload_platforms(
        config_entry, area.available_platforms()
    )

    area_data[DATA_UNDO_UPDATE_LISTENER]()
    data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(MODULE_DATA)

    return True


def migrate_seconds_to_minutes(config_data: dict) -> dict:
    """Perform migration of seconds-based config options to minutes."""

    # Update seconds -> minutes
    if CONF_CLEAR_TIMEOUT in config_data:
        config_data[CONF_CLEAR_TIMEOUT] = seconds_to_minutes(
            config_data[CONF_CLEAR_TIMEOUT], DEFAULT_CLEAR_TIMEOUT
        )
    if CONF_SECONDARY_STATES in config_data:
        entries_to_convert = {
            CONF_EXTENDED_TIMEOUT: DEFAULT_EXTENDED_TIMEOUT,
            CONF_EXTENDED_TIME: DEFAULT_EXTENDED_TIME,
            CONF_SLEEP_TIMEOUT: DEFAULT_SLEEP_TIMEOUT,
        }
        for option_key, option_value in entries_to_convert.items():
            if option_key in config_data[CONF_SECONDARY_STATES]:
                old_value = config_data[CONF_SECONDARY_STATES][option_key]
                config_data[CONF_SECONDARY_STATES][option_key] = seconds_to_minutes(
                    old_value, option_value
                )

    return config_data


# Example migration function
async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.info(
        "%s: Migrating configuration from version %s.%s, current config: %s",
        config_entry.data[ATTR_NAME],
        config_entry.version,
        config_entry.minor_version,
        str(config_entry.data),
    )

    if config_entry.version > MagicConfigEntryVersion.MAJOR:
        # This means the user has downgraded from a future version
        _LOGGER.warning(
            "%s: Major version downgrade detection, skipping migration.",
            config_entry.data[ATTR_NAME],
        )
        # FIXING MY MESS @FIXME remove before release
        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data},
            minor_version=MagicConfigEntryVersion.MINOR,
            version=MagicConfigEntryVersion.MAJOR,
        )
        # return False
        return True

    old_data = {**config_entry.data}
    new_data = {**config_entry.data}

    if config_entry.version == 1:
        new_data = migrate_seconds_to_minutes(new_data)

    if old_data != new_data:

        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            minor_version=MagicConfigEntryVersion.MINOR,
            version=MagicConfigEntryVersion.MAJOR,
        )

        _LOGGER.info(
            "Migration to configuration version %s.%s successful: %s",
            config_entry.version,
            config_entry.minor_version,
            str(new_data),
        )

    return True
