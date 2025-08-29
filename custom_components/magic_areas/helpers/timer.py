"""Reusable Timer helper for Magic Areas."""

from collections.abc import Awaitable, Callable
from datetime import datetime
import logging

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.event import async_call_later

LOGGER: logging.Logger = logging.getLogger(__name__)


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

        LOGGER.debug(
            "Initialized logger with delay=%d and callback=%s",
            self._delay,
            str(self._callback),
        )

    def start(self) -> None:
        """(Re)start the timer using the configured delay + callback."""
        self.cancel()
        self._token += 1
        token = self._token

        async def _scheduled(now: datetime) -> None:
            # Ignore if a newer start() happened after scheduling
            if token != self._token:
                LOGGER.debug("Token mismatch. Skipping (%d/%d)", self._token, token)
                return
            self._handle = None
            await self._callback(now)
            LOGGER.debug("Timer fired.")

        self._handle = async_call_later(self.hass, self._delay, _scheduled)
        LOGGER.debug("Timer started.")

    def cancel(self) -> None:
        """Cancel the timer if running."""
        if self._handle:
            self._handle()  # async_call_later returns a cancel function
            self._handle = None
            LOGGER.debug("Timer cancelled.")

    async def async_remove(self) -> None:
        """Cleanup when entity/integration is removed."""
        self.cancel()
