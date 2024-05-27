"""Magic Areas component for Home Assistant."""

from collections import defaultdict
from datetime import UTC, datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
)

from .base.magic import MagicArea, MagicMetaArea
from .const import (
    CONF_ID,
    CONF_NAME,
    DATA_AREA_OBJECT,
    DATA_ENTITY_LISTENER,
    DATA_UNDO_UPDATE_LISTENER,
    META_AREA_EXTERIOR,
    META_AREA_GLOBAL,
    META_AREA_INTERIOR,
    META_AREAS,
    MODULE_DATA,
)
from .util import get_meta_area_object

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
) -> None:
    """Set up the component."""

    def _update_config_entry() -> None:
        hass.loop.call_soon_threadsafe(
            lambda: hass.config_entries.async_update_entry(
                config_entry,
                data={**config_entry.data, "entity_ts": datetime.now(UTC)},
            )
        )

    def _async_registry_updated(event: Event[EventEntityRegistryUpdatedData]) -> None:
        # Reload entities and then update the other pieces of the system.
        _LOGGER.debug(
            "%s: Updateing entity from area change", config_entry.data[CONF_NAME]
        )
        hass.add_job(_update_config_entry)

    data = hass.data.setdefault(MODULE_DATA, {})
    area_id = config_entry.data[CONF_ID]
    area_name = config_entry.data[CONF_NAME]

    _LOGGER.debug("Setting up entry for %s", area_name)

    meta_ids = [meta_area.lower() for meta_area in META_AREAS]

    if area_id not in meta_ids:
        area_registry = async_get_ar(hass)
        area = area_registry.async_get_area(area_id)

        if not area:
            _LOGGER.debug("Could not find %s (%s) on registry", area_name, area_id)
            return False

        _LOGGER.debug("Got area %s from registry: %s", area_name, area)

        magic_area = MagicArea(
            hass,
            area,
            config_entry,
        )
    else:
        meta_area = get_meta_area_object(area_name)
        magic_area = MagicMetaArea(hass, meta_area, config_entry)

    _LOGGER.debug(
        "Magic Area %s (%s) created: %s",
        magic_area.name,
        magic_area.id,
        magic_area.config,
    )

    undo_listener = config_entry.add_update_listener(async_update_options)

    # Watch for area changes.
    entity_listener = hass.bus.async_listen(
        EVENT_ENTITY_REGISTRY_UPDATED,
        _async_registry_updated,
        _entity_registry_filter,
    )

    data[config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
        DATA_ENTITY_LISTENER: entity_listener,
    }

    # Setup platforms
    for platform in magic_area.available_platforms():
        _LOGGER.debug("Area %s: Loading platform '%s'", magic_area.name, platform)
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )
        magic_area.loaded_platforms.append(platform)

    #  Conditional reload of related meta-areas

    # Populate dict with all meta-areas with ID as key
    meta_areas: dict[str, MagicArea] = defaultdict()

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
        META_AREA_GLOBAL_ID = META_AREA_GLOBAL.lower()

        if magic_area.id != META_AREA_GLOBAL_ID and META_AREA_GLOBAL_ID in meta_areas:
            if meta_areas[META_AREA_GLOBAL_ID].initialized:
                await hass.config_entries.async_reload(
                    meta_areas[META_AREA_GLOBAL_ID].hass_config.entry_id
                )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
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
    area_data[DATA_ENTITY_LISTENER]()

    all_unloaded = all(platforms_unloaded)

    if all_unloaded:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(MODULE_DATA)

    return all_unloaded


@callback
def _entity_registry_filter(event_data: EventEntityRegistryUpdatedData) -> bool:
    """Filter entity registry events."""
    return event_data["action"] == "update" and "area_id" in event_data["changes"]
