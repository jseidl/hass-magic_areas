"""Tests for the Reusable Timer helper."""

from datetime import datetime
from unittest.mock import patch

from homeassistant.core import HomeAssistant

from custom_components.magic_areas.helpers.timer import ReusableTimer

from tests.helpers import immediate_call_factory


async def test_timer_fires(hass: HomeAssistant):
    """Test that the timer fires after the scheduled delay."""
    fired = {}

    async def callback(now: datetime):
        fired["at"] = now

    timer = ReusableTimer(hass, 0.01, callback)

    with patch(
        "custom_components.magic_areas.helpers.timer.async_call_later",
        side_effect=immediate_call_factory(hass),
    ):
        timer.start()
        await hass.async_block_till_done()

    assert "at" in fired


async def test_timer_cancel(hass: HomeAssistant):
    """Test that cancel prevents the timer from firing."""
    fired = {}

    async def callback(now: datetime):
        fired["at"] = now

    timer = ReusableTimer(hass, 0.01, callback)

    with patch(
        "custom_components.magic_areas.helpers.timer.async_call_later",
        side_effect=immediate_call_factory(hass),
    ):
        timer.start()
        timer.cancel()
        await hass.async_block_till_done()

    assert "at" not in fired


async def test_timer_restart_replaces_old(hass: HomeAssistant):
    """Test that starting a timer again cancels the previous one."""
    calls = []

    async def callback(now: datetime):
        calls.append(now)

    timer = ReusableTimer(hass, 0.01, callback)

    with patch(
        "custom_components.magic_areas.helpers.timer.async_call_later",
        side_effect=immediate_call_factory(hass),
    ):
        timer.start()  # first timer
        timer.start()  # second timer replaces first
        await hass.async_block_till_done()

    assert len(calls) == 1


async def test_async_remove_cancels(hass: HomeAssistant):
    """Test that async_remove prevents a pending timer from firing."""
    fired = {}

    async def callback(now: datetime):
        fired["at"] = now

    timer = ReusableTimer(hass, 0.01, callback)

    with patch(
        "custom_components.magic_areas.helpers.timer.async_call_later",
        side_effect=immediate_call_factory(hass),
    ):
        timer.start()
        await timer.async_remove()
        await hass.async_block_till_done()

    assert "at" not in fired
