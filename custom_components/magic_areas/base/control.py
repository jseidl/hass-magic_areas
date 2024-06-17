"""Control module for Magic Areas' controllable entities."""

from enum import StrEnum

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN

from ..const import AreaEventType, AreaState, AreaStateGroups


class AreaStateContextKey(StrEnum):
    """Keys for control context."""

    CURRENT_STATES = "states"
    NEW_STATES = "new_states"
    LOST_STATES = "lost_states"


class MagicController:
    """Base class for control of Magic entities."""

    _context: dict[str, str] = {}
    _control_enable_entity_id: str | None = None
    _required_context_keys: list[str] = [AreaStateContextKey.CURRENT_STATES]
    _enabled: bool = True

    def set_context(self, context: dict[str, str]) -> None:
        """Set context to be used in control."""
        for context_key in self._required_context_keys:
            if context_key not in context:
                raise KeyError(f"Required context key '{context_key}' not found.")

        self._context = context.copy()

    def should_control(self) -> bool:
        """Determine if entity should be controlled."""
        if self._control_enable_entity_id:
            return True  # @FIXME actually check entity state == STATE_ON

        return self._enabled

    def infer_state(self) -> str:
        """Infer if entity should be on or off."""
        raise NotImplementedError


class AreaStateBasedBinaryStateController(MagicController):
    """Basic controller for binary state sensors based off area states."""

    _on_states: list[str] | None = None
    _off_states: list[str] | None = None
    _control_on: list[str] = [AreaEventType.OCCUPANCY, AreaEventType.STATE]
    _consider_exclusive_states: bool = True
    _consider_extended_priority: bool = True
    _required_context_keys = [
        AreaStateContextKey.CURRENT_STATES,
        AreaStateContextKey.NEW_STATES,
        AreaStateContextKey.LOST_STATES,
    ]

    def __init__(
        self,
        on_states: list[str] | None = None,
        off_states: list[str] | None = None,
        control_on: list[str] | None = None,
    ) -> None:
        """Initialize the controller."""

        if control_on:
            self._control_on = control_on

        if on_states:
            self._on_states = on_states

        if off_states:
            self._off_states = off_states

    def should_control(self) -> bool:
        """Determine if entity should be controlled."""
        if not super().should_control():
            return False

        new_states = self._context[AreaStateContextKey.NEW_STATES]

        if (
            AreaState.OCCUPIED in new_states
            and AreaEventType.OCCUPANCY not in self._control_on
        ):
            return False

        if (
            AreaState.OCCUPIED not in new_states
            and AreaEventType.STATE not in self._control_on
        ):
            return False

        return True

    def _filter_on_states(self, states: list[str]) -> list[str]:
        """Filter on_states, handle extended and exclusive states."""

        filtered_list = states.copy()
        current_states = self._context[AreaStateContextKey.CURRENT_STATES]

        # Handle extended > occupied
        if self._consider_extended_priority:
            if (
                AreaState.OCCUPIED in filtered_list
                and AreaState.EXTENDED in current_states
            ):
                filtered_list.remove(AreaState.OCCUPIED)

        # Handle exclusive states
        if self._consider_exclusive_states:
            found_exclusive_states = []
            for p_state in AreaStateGroups.exclusive:
                if p_state in current_states:
                    found_exclusive_states.append(p_state)

            if not found_exclusive_states:
                return filtered_list

            for state in filtered_list:
                if state not in found_exclusive_states:
                    filtered_list.remove(state)

        return filtered_list

    def _filter_off_states(self, states: list[str]) -> list[str]:
        """Filter ofF_states. Passtrhough on base class."""
        return states

    def infer_state(self) -> str:
        """Infer if entity should be on or off."""
        _eligible_on_states = []
        _eligible_off_states = []
        current_states = self._context[AreaStateContextKey.CURRENT_STATES]

        if self._on_states:
            for state in self._on_states:
                if state in current_states:
                    _eligible_on_states.append(state)

        if self._off_states:
            for state in self._off_states:
                if state in current_states:
                    _eligible_off_states.append(state)

        # Filter out eligible states
        _eligible_on_states = self._filter_on_states(_eligible_on_states)
        _eligible_off_states = self._filter_off_states(_eligible_off_states)

        # Handle turn on cases
        if _eligible_on_states:
            return STATE_ON

        # Handle turn off cases
        if _eligible_off_states or not self._off_states:
            return STATE_OFF

        # Cannot determine, return unknown (no-op)
        return STATE_UNKNOWN


class LightStateController(AreaStateBasedBinaryStateController):
    """Control class for magic light groups."""

    def should_control(self) -> bool:
        """Determine if light should be controlled."""
        if not super().should_control():
            return False

        new_states = self._context[AreaStateContextKey.NEW_STATES]

        # Check if we're walking into a room that is already bright, we don't turn lights off just because it isn't dark
        if AreaState.BRIGHT in new_states and AreaState.OCCUPIED in new_states:
            return False

        return True

    def _filter_on_states(self, states: list[str]) -> list[str]:
        """Filter on_states, prevents lights from turning on if not dark."""
        if AreaState.DARK not in self._context[AreaStateContextKey.CURRENT_STATES]:
            return []

        return super()._filter_on_states(states)


class MediaPlayerStateController(AreaStateBasedBinaryStateController):
    """Controller class for media player groups."""

    _off_states = [AreaState.CLEAR]


class CliimateStateController(AreaStateBasedBinaryStateController):
    """Controller class for climate groups."""

    _off_states = [AreaState.CLEAR]
    _consider_extended_priority = False
    _consider_exclusive_states = False


class AreaAwareMediaPlayerStateController(AreaStateBasedBinaryStateController):
    """Controller class for area-aware media player."""

    _consider_extended_priority = False
