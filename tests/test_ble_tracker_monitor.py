"""Tests for the BLE Tracker feature."""

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from custom_components.magic_areas.const import ATTR_PRESENCE_SENSORS

from tests.const import DEFAULT_MOCK_AREA
from tests.mocks import MockSensor


async def test_ble_tracker_presence_sensor(
    hass: HomeAssistant,
    entities_ble_sensor_one: list[MockSensor],
    _setup_integration_ble_tracker,
) -> None:
    """Test BLE tracker monitor functionality."""

    ble_sensor_entity_id = "sensor.ble_tracker_1"
    ble_tracker_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_ble_trackers_{DEFAULT_MOCK_AREA.value}_ble_tracker_monitor"
    area_sensor_entity_id = f"{BINARY_SENSOR_DOMAIN}.magic_areas_presence_tracking_{DEFAULT_MOCK_AREA.value}_area_state"

    hass.states.async_set(ble_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)

    assert ble_sensor_state is not None
    assert ble_sensor_state.state is not None

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)

    assert ble_tracker_state is not None
    assert ble_tracker_state.state == STATE_OFF
    assert ble_sensor_entity_id in ble_tracker_state.attributes[ATTR_ENTITY_ID]

    area_sensor_state = hass.states.get(area_sensor_entity_id)

    assert area_sensor_state is not None
    assert area_sensor_state.state == STATE_OFF
    assert ble_tracker_entity_id in area_sensor_state.attributes[ATTR_PRESENCE_SENSORS]

    # Set BLE sensor to DEFAULT_MOCK_AREA
    hass.states.async_set(ble_sensor_entity_id, DEFAULT_MOCK_AREA.value)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)

    assert ble_sensor_state is not None
    assert ble_sensor_state.state == DEFAULT_MOCK_AREA.value

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)

    assert ble_tracker_state is not None
    assert ble_tracker_state.state == STATE_ON

    area_sensor_state = hass.states.get(area_sensor_entity_id)

    assert area_sensor_state is not None
    assert area_sensor_state.state == STATE_ON

    # Set BLE sensor to something else
    hass.states.async_set(ble_sensor_entity_id, STATE_UNKNOWN)
    await hass.async_block_till_done()

    ble_sensor_state = hass.states.get(ble_sensor_entity_id)

    assert ble_sensor_state is not None
    assert ble_sensor_state.state == STATE_UNKNOWN

    ble_tracker_state = hass.states.get(ble_tracker_entity_id)

    assert ble_tracker_state is not None
    assert ble_tracker_state.state == STATE_OFF

    area_sensor_state = hass.states.get(area_sensor_entity_id)

    assert area_sensor_state is not None
    assert area_sensor_state.state == STATE_OFF
