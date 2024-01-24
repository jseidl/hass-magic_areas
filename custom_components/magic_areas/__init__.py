"""Magic Areas component for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .base import MagicArea, MagicMetaArea
from .const import (
    CONF_ID,
    CONF_NAME,
    DATA_AREA_OBJECT,
    DATA_UNDO_UPDATE_LISTENER,
    META_AREAS,
    MODULE_DATA,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""
    data = hass.data.setdefault(MODULE_DATA, {})
    area_id = config_entry.data[CONF_ID]
    area_name = config_entry.data[CONF_NAME]

    _LOGGER.debug(f"Setting up entry for {area_name}")

    meta_ids = [meta_area.lower() for meta_area in META_AREAS]

    if area_id not in meta_ids:
        area_registry = hass.helpers.area_registry.async_get(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.debug(f"Could not find {area_name} ({area_id}) on registry")
            return False

        _LOGGER.debug(f"Got area {area_name} from registry: {area}")

        magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )
    else:
        magic_area = MagicMetaArea(hass, area_name, config_entry)

    _LOGGER.debug(
        f"Magic Area {magic_area.name} ({magic_area.id}) created: {magic_area.config}"
    )

    undo_listener = config_entry.add_update_listener(async_update_options)

    data[config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
    }

    return True


async def async_update_options(hass, config_entry: ConfigEntry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)

    # Check if we need to reload meta entities
    data = hass.data[MODULE_DATA]
    area = data[config_entry.entry_id][DATA_AREA_OBJECT]

    if not area.is_meta():
        meta_ids = []
        _LOGGER.debug(f"Area not meta, reloading meta areas.")
        for entry_id, area_data in data.items():
            area = area_data[DATA_AREA_OBJECT]
            if area.is_meta():
                meta_ids.append(entry_id)

        for entry_id in meta_ids:
            await hass.config_entries.async_reload(entry_id)
        _LOGGER.debug(f"Meta areas reloaded.")


async def async_unload_entry(hass, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    platforms_unloaded = []
    data = hass.data[MODULE_DATA]
    area_data = data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    for platform in area.loaded_platforms:
        unload_ok = await hass.config_entries.async_forward_entry_unload(
            config_entry, platform
        )
        platforms_unloaded.append(unload_ok)

    area_data[DATA_UNDO_UPDATE_LISTENER]()

    all_unloaded = all(platforms_unloaded)

    if all_unloaded:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(MODULE_DATA)

    return all_unloaded
