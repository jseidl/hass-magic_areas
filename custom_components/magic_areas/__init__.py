"""Magic Areas component for Home Assistant."""

from datetime import UTC, datetime
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EventEntityRegistryUpdatedData,
)

from custom_components.magic_areas.base.magic import MagicArea
from custom_components.magic_areas.const import (
    DATA_AREA_OBJECT,
    DATA_ENTITY_LISTENER,
    DATA_UNDO_UPDATE_LISTENER,
    MODULE_DATA,
    MagicConfigEntryVersion,
)
from custom_components.magic_areas.helpers.area import get_magic_area_for_config_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up the component."""

    @callback
    def _async_registry_updated(event: Event[EventEntityRegistryUpdatedData]) -> None:
        """Reload integration when entity registry is updated."""

        _LOGGER.debug(
            "%s: Reloading entry due entity registry change",
            config_entry.data[ATTR_NAME],
        )
        hass.config_entries.async_update_entry(
            config_entry,
            data={**config_entry.data, "entity_ts": datetime.now(UTC)},
        )

    hass.data.setdefault(MODULE_DATA, {})

    magic_area: MagicArea = get_magic_area_for_config_entry(hass, config_entry)
    assert magic_area is not None
    await magic_area.initialize()

    _LOGGER.debug(
        "%s: Magic Area (%s) created: %s",
        magic_area.name,
        magic_area.id,
        str(magic_area.config),
    )

    # Setup config uptate listener
    undo_listener = config_entry.add_update_listener(async_update_options)

    # Watch for area changes.
    entity_listener = hass.bus.async_listen(
        EVENT_ENTITY_REGISTRY_UPDATED,
        _async_registry_updated,
        _entity_registry_filter,
    )

    hass.data[MODULE_DATA][config_entry.entry_id] = {
        DATA_AREA_OBJECT: magic_area,
        DATA_UNDO_UPDATE_LISTENER: undo_listener,
        DATA_ENTITY_LISTENER: entity_listener,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(
        config_entry, magic_area.available_platforms()
    )

    return True


async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug(
        "Detected options change for entry %s, reloading", config_entry.entry_id
    )
    await hass.config_entries.async_reload(config_entry.entry_id)

    # @TODO Reload corresponding meta areas (floor+interior/exterior+global)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    platforms_unloaded = []
    data = hass.data[MODULE_DATA]

    if config_entry.entry_id not in data:
        _LOGGER.debug(
            "Config entry '%s' not on data dictionary, probably already unloaded. Skipping.",
            config_entry.entry_id,
        )
        return True

    area_data = data[config_entry.entry_id]
    area = area_data[DATA_AREA_OBJECT]

    for platform in area.available_platforms():
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

    return True


# Update config version
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

        return False

    hass.config_entries.async_update_entry(
        config_entry,
        minor_version=MagicConfigEntryVersion.MINOR,
        version=MagicConfigEntryVersion.MAJOR,
    )

    _LOGGER.info(
        "Migration to configuration version %s.%s successful: %s",
        config_entry.version,
        config_entry.minor_version,
        str(config_entry.data),
    )

    return True


@callback
def _entity_registry_filter(event_data: EventEntityRegistryUpdatedData) -> bool:
    """Filter entity registry events."""
    return event_data["action"] == "update" and "area_id" in event_data["changes"]
