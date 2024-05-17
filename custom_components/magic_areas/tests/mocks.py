"""Fake light for testing with."""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant import auth, bootstrap, config_entries, loader
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import call_later

TURN_ON_ARG_TO_COLOR_MODE = {
    "hs_color": ColorMode.HS,
    "xy_color": ColorMode.XY,
    "rgb_color": ColorMode.RGB,
    "rgbw_color": ColorMode.RGBW,
    "rgbww_color": ColorMode.RGBWW,
    "color_temp_kelvin": ColorMode.COLOR_TEMP,
}


class MockToggleEntity(ToggleEntity):
    """Provide a mock toggle device."""

    def __init__(self, name, state, unique_id=None):
        """Initialize the mock entity."""
        self._name = name or DEVICE_DEFAULT_NAME
        self._state = state
        self.calls = []

    @property
    def name(self):
        """Return the name of the entity if any."""
        self.calls.append(("name", {}))
        return self._name

    @property
    def state(self):
        """Return the state of the entity if any."""
        self.calls.append(("state", {}))
        return self._state

    @property
    def is_on(self):
        """Return true if entity is on."""
        self.calls.append(("is_on", {}))
        return self._state == STATE_ON

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        self.calls.append(("turn_on", kwargs))
        self._state = STATE_ON

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        self.calls.append(("turn_off", kwargs))
        self._state = STATE_OFF

    def last_call(self, method=None):
        """Return the last call."""
        if not self.calls:
            return None
        if method is None:
            return self.calls[-1]
        try:
            return next(call for call in reversed(self.calls) if call[0] == method)
        except StopIteration:
            return None


class MockLight(MockToggleEntity, LightEntity):
    """Mock light class."""

    _attr_max_color_temp_kelvin = 6500
    _attr_min_color_temp_kelvin = 2000
    supported_features = 0

    brightness = None
    color_temp_kelvin = None
    hs_color = None
    rgb_color = None
    rgbw_color = None
    rgbww_color = None
    xy_color = None

    def __init__(
        self,
        name: str,
        state: str,
        unique_id: str = None,
        supported_color_modes: set[ColorMode] | None = None,
    ) -> None:
        """Initialize the mock light."""
        super().__init__(name, state, unique_id)
        if supported_color_modes is None:
            supported_color_modes = {ColorMode.ONOFF}
        self._attr_supported_color_modes = supported_color_modes
        color_mode = ColorMode.UNKNOWN
        if len(supported_color_modes) == 1:
            color_mode = next(iter(supported_color_modes))
        self._attr_color_mode = color_mode

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        super().turn_on(**kwargs)
        for key, value in kwargs.items():
            if key in [
                "brightness",
                "hs_color",
                "xy_color",
                "rgb_color",
                "rgbw_color",
                "rgbww_color",
                "color_temp_kelvin",
            ]:
                setattr(self, key, value)
            if key == "white":
                setattr(self, "brightness", value)
            if key in TURN_ON_ARG_TO_COLOR_MODE:
                self._attr_color_mode = TURN_ON_ARG_TO_COLOR_MODE[key]


class MockPlatform:
    """Provide a fake platform."""

    __name__ = "homeassistant.components.light.bla"
    __file__ = "homeassistant/components/blah/light"

    def __init__(
        self,
        setup_platform=None,
        dependencies=None,
        platform_schema=None,
        async_setup_platform=None,
        async_setup_entry=None,
        scan_interval=None,
    ):
        """Initialize the platform."""
        self.DEPENDENCIES = dependencies or []

        if platform_schema is not None:
            self.PLATFORM_SCHEMA = platform_schema

        if scan_interval is not None:
            self.SCAN_INTERVAL = scan_interval

        if setup_platform is not None:
            # We run this in executor, wrap it in function
            self.setup_platform = lambda *args: setup_platform(*args)

        if async_setup_platform is not None:
            self.async_setup_platform = async_setup_platform

        if async_setup_entry is not None:
            self.async_setup_entry = async_setup_entry

        if setup_platform is None and async_setup_platform is None:
            self.async_setup_platform = AsyncMock(return_value=None)


class MockModule:
    """Representation of a fake module."""

    def __init__(
        self,
        domain=None,
        dependencies=None,
        setup=None,
        requirements=None,
        config_schema=None,
        platform_schema=None,
        platform_schema_base=None,
        async_setup=None,
        async_setup_entry=None,
        async_unload_entry=None,
        async_migrate_entry=None,
        async_remove_entry=None,
        partial_manifest=None,
        async_remove_config_entry_device=None,
    ) -> None:
        """Initialize the mock module."""
        self.__name__ = f"homeassistant.components.{domain}"
        self.__file__ = f"homeassistant/components/{domain}"
        self.DOMAIN = domain
        self.DEPENDENCIES = dependencies or []
        self.REQUIREMENTS = requirements or []
        # Overlay to be used when generating manifest from this module
        self._partial_manifest = partial_manifest

        if config_schema is not None:
            self.CONFIG_SCHEMA = config_schema

        if platform_schema is not None:
            self.PLATFORM_SCHEMA = platform_schema

        if platform_schema_base is not None:
            self.PLATFORM_SCHEMA_BASE = platform_schema_base

        if setup:
            # We run this in executor, wrap it in function
            self.setup = lambda *args: setup(*args)

        if async_setup is not None:
            self.async_setup = async_setup

        if setup is None and async_setup is None:
            self.async_setup = AsyncMock(return_value=True)

        if async_setup_entry is not None:
            self.async_setup_entry = async_setup_entry

        if async_unload_entry is not None:
            self.async_unload_entry = async_unload_entry

        if async_migrate_entry is not None:
            self.async_migrate_entry = async_migrate_entry

        if async_remove_entry is not None:
            self.async_remove_entry = async_remove_entry

        if async_remove_config_entry_device is not None:
            self.async_remove_config_entry_device = async_remove_config_entry_device

    def mock_manifest(self):
        """Generate a mock manifest to represent this module."""
        return {
            **loader.manifest_from_legacy_module(self.DOMAIN, self),
            **(self._partial_manifest or {}),
        }
