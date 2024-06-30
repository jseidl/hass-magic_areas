"""Base classes for handling configuration options."""

from collections.abc import Callable, Iterator
from typing import Any

import voluptuous as vol

from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    selector,
)


class NullableEntitySelector(EntitySelector):
    """Entity selector that supports null values."""

    def __call__(self, data):
        """Validate the passed selection, if passed."""

        if data in (None, ""):
            return data

        return super().__call__(data)


class ConfigOptionSelector:
    """Build selectors for config UI."""

    @staticmethod
    def select(options=None, multiple=False):
        """Build a <select> selector."""
        if not options:
            options = []
        return selector(
            {"select": {"options": options, "multiple": multiple, "mode": "dropdown"}}
        )

    @staticmethod
    def entity(options=None, multiple=False, force_include=False):
        """Build a <select> selector with predefined settings."""
        if not options:
            options = []
        return NullableEntitySelector(
            EntitySelectorConfig(include_entities=options, multiple=multiple)
        )

    @staticmethod
    def number(min_value=0, max_value=9999, mode="box", unit_of_measurement="seconds"):
        """Build a number selector."""
        return selector(
            {
                "number": {
                    "min": min_value,
                    "max": max_value,
                    "mode": mode,
                    "unit_of_measurement": unit_of_measurement,
                }
            }
        )


class MagicAreasConfigOption:
    """Information about a configuration option."""

    key: str
    validator: Callable[...] | None
    default: Any
    required: bool
    configurable: bool
    options: list | None
    current: Any

    def __init__(
        self,
        key: str,
        validator: Callable[...] | None = None,
        default: Any = None,
        options: list | None = None,
        configurable: bool = True,
        required: bool = False,
    ) -> None:
        """Initialize the option."""

        self.key = key
        self.validator = validator
        self.default = default
        self.configurable = configurable
        self.required = required
        self.options = options
        self.current = None

    def value(self) -> Any:
        """Return current value if set, default otherwise."""
        return self.current if self.current else self.default


class MagicAreasConfigOptionSet:
    """Set of configuration options."""

    key: str
    active: bool = False
    options: list[MagicAreasConfigOption]
    _option_map: dict[str, MagicAreasConfigOption]

    def __init__(self) -> None:
        """Initialize option set."""

        for option in self.options:
            self._option_map[option.key] = option

    def get(self, option_key: str) -> MagicAreasConfigOption:
        """Return an option by key."""

        if option_key not in self._option_map:
            raise ValueError(f"Invalid option: {option_key}")

        return self._option_map.get(option_key)

    def load(self, options: dict) -> None:
        """Load current values for options from a dict."""
        # Validate input
        schema = self.generate_schema()
        validated_input = schema(options)

        # Save values
        for option_k, option_v in validated_input.items():
            if option_k not in self._option_map:
                continue
            self._option_map[option_k].current = option_v

        # Set as active
        self.active = True

    def get_configurable_options(self) -> Iterator[MagicAreasConfigOption]:
        """Return MagicArasConfigOption that area configurable."""

        for option in self.options:
            if not option.configurable:
                continue
            yield option

    def get_values(self) -> dict[str, str]:
        """Return a dictionary with the key => value pairs."""

        values_dict = {}

        for option in self.get_configurable_options():
            values_dict[option.key] = option.value()

        return values_dict

    def generate_options(self) -> list[tuple]:
        """Generate options for config_flow."""
        option_list = []

        for option in self.get_configurable_options():
            option_list.append((option.key, option.default, option.validator))

        return option_list

    def generate_schema(self, as_object: bool = True) -> dict[Callable, Callable]:
        """Generate schema for voluptuous."""

        schema_dict = {}

        for option in self.get_configurable_options():

            vol_object = vol.Required if option.required else vol.Optional
            schema_key = vol_object(option.key, default=option.default)
            schema_value = option.validator

            if option.options:
                schema_value = vol.In(option.options)

            if isinstance(option.type, list):
                schema_value = vol.Any(option.validator)

            schema_dict[schema_key] = schema_value

        return vol.Schema(schema_dict) if as_object else schema_dict
