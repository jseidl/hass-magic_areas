"""Common code for running the tests."""

from asyncio import get_running_loop
from collections.abc import Sequence
import functools
import logging
import pathlib
from typing import NoReturn
from unittest.mock import Mock, patch

import voluptuous as vol

from homeassistant import loader
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .mocks import MockModule, MockPlatform

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


def setup_mqtt_room_component_platform(
    hass: HomeAssistant,
    domain: str,
    entities: Sequence[Entity],
    from_config_entry: bool = False,
    built_in: bool = True,
) -> MockPlatform:
    """Mock a mqtt room component platform for tests."""

    _LOGGER.info("Setting up mqtt room platform")

    async def _async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
    ) -> None:
        """Set up a mqtt room component platform."""
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
            """Set up a mqtt room component platform."""
            async_add_entities(entities)

        platform.async_setup_entry = _async_setup_entry
        platform.async_setup_platform = None

    mock_platform(hass, f"mqtt_room.{domain}", platform, built_in=built_in)
    return platform


def mock_integration(
    hass: HomeAssistant, module: MockModule, built_in: bool = True
) -> loader.Integration:
    """Mock an integration."""
    integration = loader.Integration(
        hass,
        (
            f"{loader.PACKAGE_BUILTIN}.{module.DOMAIN}"
            if built_in
            else f"{loader.PACKAGE_CUSTOM_COMPONENTS}.{module.DOMAIN}"
        ),
        pathlib.Path(""),
        module.mock_manifest(),
        set(),
    )

    def mock_import_platform(platform_name: str) -> NoReturn:
        raise ImportError(
            f"Mocked unable to import platform '{integration.pkg_path}.{platform_name}'",
            name=f"{integration.pkg_path}.{platform_name}",
        )

    # pylint: disable-next=protected-access
    integration._import_platform = mock_import_platform

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

    # pylint: disable-next=protected-access
    integration_cache[domain]._top_level_files.add(f"{platform_name}.py")
    _LOGGER.info("Adding mock integration platform: %s", platform_path)
    module_cache[platform_path] = module or Mock()


def async_mock_service(
    hass: HomeAssistant,
    domain: str,
    service: str,
    schema: vol.Schema | None = None,
    response: ServiceResponse = None,
    supports_response: SupportsResponse | None = None,
    raise_exception: Exception | None = None,
) -> list[ServiceCall]:
    """Set up a fake service & return a calls log list to this service."""
    calls = []

    @callback
    def mock_service_log(call):  # pylint: disable=unnecessary-lambda
        """Mock service call."""
        calls.append(call)
        if raise_exception is not None:
            raise raise_exception
        return response

    if supports_response is None:
        if response is not None:
            supports_response = SupportsResponse.OPTIONAL
        else:
            supports_response = SupportsResponse.NONE

    hass.services.async_register(
        domain,
        service,
        mock_service_log,
        schema=schema,
        supports_response=supports_response,
    )

    return calls


class VirtualClock:
    """Provide a virtual clock for an asyncio event loop.

    This makes timing-based tests deterministic and instantly completed.
    """

    def __init__(self) -> None:
        """Initialize the clock with a simple time."""
        self.vtime = 0.0

    def virtual_time(self) -> float:
        """Return the current virtual time."""
        return self.vtime

    def _virtual_select(self, orig_select, timeout):
        if timeout is not None:
            self.vtime += timeout
        return orig_select(0)  # override the timeout to zero

    def patch_loop(self):
        """Override some methods of the current event loop.

        This is so that sleep instantly returns while proceeding the virtual clock.
        """
        loop = get_running_loop()
        with (
            patch.object(
                loop._selector,  # pylint: disable=protected-access
                "select",
                new=functools.partial(
                    self._virtual_select,
                    loop._selector.select,  # pylint: disable=protected-access
                ),
            ),
            patch.object(
                loop,
                "time",
                new=self.virtual_time,
            ),
            patch.object(
                loop,
                "_clock_resolution",
                new=0.1,
            ),
        ):
            yield
