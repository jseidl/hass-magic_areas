"""Test for cover groups."""

from collections import defaultdict
import logging

from homeassistant.components.cover import DOMAIN as COVER_DOMAIN, CoverDeviceClass
from homeassistant.const import ATTR_DEVICE_CLASS, ATTR_ENTITY_ID, STATE_OPEN
from homeassistant.core import HomeAssistant

from .mocks import MockCover

_LOGGER = logging.getLogger(__name__)


async def test_cover_group_basic(
    hass: HomeAssistant,
    entities_sensor_cover_all_classes_multiple: list[MockCover],
    _setup_integration_cover_group,
) -> None:
    """Test the light from illuminance threshold sensor."""

    cover_group_entity_id_base = (
        f"{COVER_DOMAIN}.magic_areas_cover_groups_kitchen_cover_group_"
    )
    entity_map = defaultdict(list)

    # Ensure all mock entities exist and map
    for cover in entities_sensor_cover_all_classes_multiple:
        cover_state = hass.states.get(cover.entity_id)
        assert cover_state is not None
        assert cover_state.state == STATE_OPEN
        entity_map[cover_state.attributes[ATTR_DEVICE_CLASS]].append(cover)

    for dc in CoverDeviceClass:
        group_entity_id = f"{cover_group_entity_id_base}{dc.value}"

        # Ensure cover group exists and has its children
        group_entity_state = hass.states.get(group_entity_id)
        assert group_entity_state is not None
        assert group_entity_state.state == STATE_OPEN
        for child_cover in entity_map[dc.value]:
            assert (
                child_cover.entity_id in group_entity_state.attributes[ATTR_ENTITY_ID]
            )
