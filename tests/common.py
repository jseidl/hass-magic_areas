"""Shared functions for tests"""

import logging

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.magic_areas.const import (
    _DOMAIN_SCHEMA,
    DOMAIN,
)

from homeassistant.const import CONF_ID, CONF_NAME
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN, BinarySensorDeviceClass
from homeassistant.setup import async_setup_component
from homeassistant.util import slugify

from .const import MOCK_AREA_NAME, MOCK_PRESENCE_SENSOR_NAME, MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID, MOCK_PRESENCE_BINARY_SENSOR_UNIQUEID, NOCK_PRESENCE_INPUT_BOOLEAN_ID, MOCK_PRESENCE_SENSOR_SLUG, NOCK_PRESENCE_BINARY_SENSOR_ID

LOGGER = logging.getLogger(__name__)

async def setup_area_with_presence_sensor(hass, extra_opts=None):

    # Create mock input boolean and presence sensor
    input_boolean_opts = {
        f"{MOCK_PRESENCE_SENSOR_SLUG}": {
            "name": MOCK_PRESENCE_SENSOR_NAME,
        }
    }
    value_template = "{{ is_state('EID', 'on') }}"
    LOGGER.warning(value_template)
    binary_sensor_opts = {
        "platform": "template",
        "sensors": {
            f"{MOCK_PRESENCE_SENSOR_SLUG}": {
                "friendly_name": MOCK_PRESENCE_SENSOR_NAME,
                "value_template": value_template.replace("EID", NOCK_PRESENCE_INPUT_BOOLEAN_ID),
                "device_class": BinarySensorDeviceClass.PRESENCE,
                "unique_id": MOCK_PRESENCE_BINARY_SENSOR_UNIQUEID
            }
        }
    }

    await async_setup_component(
        hass,
        INPUT_BOOLEAN_DOMAIN,
        {INPUT_BOOLEAN_DOMAIN: input_boolean_opts},
    )
    await hass.async_block_till_done()
    await async_setup_component(
        hass,
        BINARY_SENSOR_DOMAIN,
        {BINARY_SENSOR_DOMAIN: binary_sensor_opts},
    )
    await hass.async_block_till_done()

    assert hass.states.get(NOCK_PRESENCE_INPUT_BOOLEAN_ID) is not None
    assert hass.states.get(NOCK_PRESENCE_BINARY_SENSOR_ID) is not None

    # Create test area
    area_registry = hass.helpers.area_registry.async_get(hass)
    test_area = area_registry.async_get_or_create(MOCK_AREA_NAME)

    # Add presence sensor to new area
    entity_registry = hass.helpers.entity_registry.async_get(hass)
    entity = entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        "template",
        MOCK_PRESENCE_BINARY_SENSOR_UNIQUEID
    )
    entity_registry.async_update_entity(
        entity.entity_id,
        area_id=test_area.id,
    )
    await hass.async_block_till_done()

    # Setup MA
    entry = await setup_area(hass, test_area, extra_opts)

    # Check that presence sensor is added
    state = hass.states.get(MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID)

    assert entity.entity_id in state.attributes['presence_sensors']

    return entry

async def setup_area(hass, test_area = None, extra_opts=None):

    if not test_area:
        area_registry = hass.helpers.area_registry.async_get(hass)
        test_area = area_registry.async_get_or_create(MOCK_AREA_NAME)

    assert test_area is not None

    LOGGER.info("Got mock area: %s", str(test_area))

    config_entry_data = _DOMAIN_SCHEMA({f"{test_area.id}": {}})[test_area.id]
    area_opts = {CONF_ID: test_area.id, CONF_NAME: test_area.name}
    config_entry_data.update(area_opts)

    if extra_opts:
        config_entry_data.update(extra_opts)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_entry_data,
    )

    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await hass.async_start()
    await hass.async_block_till_done()

    return entry