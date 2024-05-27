"""Magic Areas Test Constants."""

import hashlib

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.util import slugify

# Mock entities
MOCK_AREA_NAME = "MagicAreas Test Area"
MOCK_AREA_PRESENCE_SENSOR_NAME = slugify(f"Area {MOCK_AREA_NAME}")
MOCK_AREA_PRESENCE_SENSOR_ENTITY_ID = (
    f"{BINARY_SENSOR_DOMAIN}.{MOCK_AREA_PRESENCE_SENSOR_NAME}"
)
MOCK_AREA_CLEAR_TIMEOUT = 3

MOCK_PRESENCE_SENSOR_NAME = "MagicAreas Test Presence"
MOCK_PRESENCE_SENSOR_SLUG = slugify(MOCK_PRESENCE_SENSOR_NAME)
NOCK_PRESENCE_INPUT_BOOLEAN_ID = f"input_boolean.{MOCK_PRESENCE_SENSOR_SLUG}"
NOCK_PRESENCE_BINARY_SENSOR_ID = f"binary_sensor.{MOCK_PRESENCE_SENSOR_SLUG}"
MOCK_PRESENCE_BINARY_SENSOR_UNIQUEID = hashlib.sha256(
    NOCK_PRESENCE_BINARY_SENSOR_ID.encode("utf-8")
).hexdigest()
