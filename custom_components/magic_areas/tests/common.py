"""Common code for running the tests."""

from collections.abc import Generator, Sequence
import logging
import pathlib
from typing import Any, NoReturn, TypeVar
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import (
    CONF_ID,
    CONF_NAME,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import auth, bootstrap, config_entries, loader
from homeassistant.components import light
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_get_ar
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_er
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.setup import async_setup_component

from .mocks import MockLight, MockModule, MockPlatform

_LOGGER = logging.getLogger(__name__)


def setup_test_component_platform(
    hass: HomeAssistant,
    domain: str,
    entities: Sequence[Entity],
    from_config_entry: bool = False,
    built_in: bool = True,
) -> MockPlatform:
    """Mock a test component platform for tests."""

    async def _async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> None:
        """Set up a test component platform."""
        async_add_entities(entities)

    platform = MockPlatform(
        async_setup_platform=_async_setup_platform,
    )

    # avoid creating config entry setup if not needed
    if from_config_entry:

        async def _async_setup_entry(
            hass: HomeAssistant,
            entry: ConfigEntry,
            async_add_entities: AddEntitiesCallback,
        ) -> None:
            """Set up a test component platform."""
            async_add_entities(entities)

        platform.async_setup_entry = _async_setup_entry
        platform.async_setup_platform = None

    mock_platform(hass, f"test.{domain}", platform, built_in=built_in)
    return platform


def mock_integration(
    hass: HomeAssistant, module: MockModule, built_in: bool = True
) -> loader.Integration:
    """Mock an integration."""
    integration = loader.Integration(
        hass,
        f"{loader.PACKAGE_BUILTIN}.{module.DOMAIN}"
        if built_in
        else f"{loader.PACKAGE_CUSTOM_COMPONENTS}.{module.DOMAIN}",
        pathlib.Path(""),
        module.mock_manifest(),
        set(),
    )

    def mock_import_platform(platform_name: str) -> NoReturn:
        raise ImportError(
            f"Mocked unable to import platform '{integration.pkg_path}.{platform_name}'",
            name=f"{integration.pkg_path}.{platform_name}",
        )

    integration._import_platform = mock_import_platform  # noqa: SLF001

    _LOGGER.info("Adding mock integration: %s", module.DOMAIN)
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    integration_cache[module.DOMAIN] = integration

    module_cache = hass.data[loader.DATA_COMPONENTS]
    module_cache[module.DOMAIN] = module

    return integration


def mock_platform(
    hass: HomeAssistant,
    platform_path: str,
    module: Mock | MockPlatform | None = None,
    built_in=True,
) -> None:
    """Mock a platform.

    platform_path is in form hue.config_flow.
    """
    domain, _, platform_name = platform_path.partition(".")
    integration_cache = hass.data[loader.DATA_INTEGRATIONS]
    module_cache = hass.data[loader.DATA_COMPONENTS]

    if domain not in integration_cache:
        mock_integration(hass, MockModule(domain), built_in=built_in)

    integration_cache[domain]._top_level_files.add(f"{platform_name}.py")  # noqa: SLF001
    _LOGGER.info("Adding mock integration platform: %s", platform_path)
    module_cache[platform_path] = module or Mock()
