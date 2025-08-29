"""Reusable Timer helper for Magic Areas."""

from collections.abc import Awaitable, Callable
from datetime import datetime

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_call_later


class ReusableTimer:
    """Single active reusable timer with fixed delay and callback."""

    def __init__(
        self,
        hass: HomeAssistant,
        delay: float,
        callback: Callable[[datetime], Awaitable[None]],
    ) -> None:
        """Initialize the timer with a fixed delay and async callback."""
        self.hass = hass
        self._delay = delay
        self._callback = callback
        self._handle: CALLBACK_TYPE | None = None
        self._token: int = 0  # protects against race conditions

    def start(self) -> None:
        """(Re)start the timer using the configured delay + callback."""
        self.cancel()
        self._token += 1
        token = self._token

        async def _scheduled(now: datetime) -> None:
            # Ignore if a newer start() happened after scheduling
            if token != self._token:
                return
            self._handle = None
            await self._callback(now)

        self._handle = async_call_later(self.hass, self._delay, _scheduled)

    def cancel(self) -> None:
        """Cancel the timer if running."""
        if self._handle:
            self._handle()  # async_call_later returns a cancel function
            self._handle = None

    async def async_remove(self) -> None:
        """Cleanup when entity/integration is removed."""
        self.cancel()
