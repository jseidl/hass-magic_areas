"""Fake light for testing with."""

from typing import Any, Final
from unittest.mock import AsyncMock

from homeassistant import loader
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.light import ColorMode, LightEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity, EntityCategory, ToggleEntity

TURN_ON_ARG_TO_COLOR_MODE = {
    "hs_color": ColorMode.HS,
    "xy_color": ColorMode.XY,
    "rgb_color": ColorMode.RGB,
    "rgbw_color": ColorMode.RGBW,
    "rgbww_color": ColorMode.RGBWW,
    "color_temp_kelvin": ColorMode.COLOR_TEMP,
}

# If no name is specified
DEVICE_DEFAULT_NAME: Final = "Unnamed Device"


class MockToggleEntity(ToggleEntity):
    """Provide a mock toggle device."""

    def __init__(self, name: str, state: str, unique_id: str | None = None) -> None:
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

    brightness: int | None = None
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
        unique_id: str | None = None,
        dimmable: bool | None = None,
    ) -> None:
        """Initialize the mock light."""
        super().__init__(name, state, unique_id)
        if dimmable:
            self.color_mode = ColorMode.RGBWW
            self.hs_color = "Invalid"  # Should be ignored
            self.rgb_color = "Invalid"  # Should be ignored
            self.rgbw_color = "Invalid"  # Should be ignored
            self.rgbww_color = (1, 2, 3, 4, 5)
            self.xy_color = "Invalid"  # Should be ignored
            self.brightness = 255
        else:
            self.color_mode = {ColorMode.ONOFF}

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
    ) -> None:
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


class MockEntity(Entity):
    """Mock Entity class."""

    def __init__(self, **values: Any) -> None:
        """Initialize an entity."""
        self._values = values

        if "entity_id" in values:
            self.entity_id = values["entity_id"]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._handle("available")

    @property
    def capability_attributes(self) -> dict[str, Any] | None:
        """Info about capabilities."""
        return self._handle("capability_attributes")

    @property
    def device_class(self) -> str | None:
        """Info how device should be classified."""
        return self._handle("device_class")

    @property
    def device_info(self) -> DeviceInfo | None:
        """Info how it links to a device."""
        return self._handle("device_info")

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the entity category."""
        return self._handle("entity_category")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        return self._handle("extra_state_attributes")

    @property
    def has_entity_name(self) -> bool:
        """Return the has_entity_name name flag."""
        return self._handle("has_entity_name")

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._handle("entity_registry_enabled_default")

    @property
    def entity_registry_visible_default(self) -> bool:
        """Return if the entity should be visible when first added to the entity registry."""
        return self._handle("entity_registry_visible_default")

    @property
    def icon(self) -> str | None:
        """Return the suggested icon."""
        return self._handle("icon")

    @property
    def name(self) -> str | None:
        """Return the name of the entity."""
        return self._handle("name")

    @property
    def should_poll(self) -> bool:
        """Return the ste of the polling."""
        return self._handle("should_poll")

    @property
    def supported_features(self) -> int | None:
        """Info about supported features."""
        return self._handle("supported_features")

    @property
    def translation_key(self) -> str | None:
        """Return the translation key."""
        return self._handle("translation_key")

    @property
    def unique_id(self) -> str | None:
        """Return the unique ID of the entity."""
        return self._handle("unique_id")

    @property
    def unit_of_measurement(self) -> str | None:
        """Info on the units the entity state is in."""
        return self._handle("unit_of_measurement")

    def _handle(self, attr: str) -> Any:
        """Return attribute value."""
        if attr in self._values:
            return self._values[attr]
        return getattr(super(), attr)


class MockBinarySensor(MockEntity, BinarySensorEntity):
    """Mock Binary Sensor class."""

    _state = STATE_OFF

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state == STATE_ON

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        self._state = STATE_ON
        self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        self._state = STATE_OFF
        self.schedule_update_ha_state()

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._handle("device_class")
