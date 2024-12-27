"""Constants for Magic Areas tests."""

from enum import StrEnum, auto

from homeassistant.const import ATTR_FLOOR_ID

from custom_components.magic_areas.const import CONF_TYPE, AreaType


class MockAreaIds(StrEnum):
    """StrEnum with ids of Mock Areas."""

    KITCHEN = auto()
    LIVING_ROOM = auto()
    DINING_ROOM = auto()
    MASTER_BEDROOM = auto()
    GUEST_BEDROOM = auto()
    GARAGE = auto()
    BACKYARD = auto()
    FRONT_YARD = auto()
    INTERIOR = auto()
    EXTERIOR = auto()
    GLOBAL = auto()
    GROUND_LEVEL = auto()
    FIRST_FLOOR = auto()
    SECOND_FLOOR = auto()


class MockFloorIds(StrEnum):
    """StrEnum with ids of Mock Floors."""

    GROUND_LEVEL = auto()
    FIRST_FLOOR = auto()
    SECOND_FLOOR = auto()


FLOOR_LEVEL_MAP: dict[MockFloorIds, int] = {
    MockFloorIds.GROUND_LEVEL: 0,
    MockFloorIds.FIRST_FLOOR: 1,
    MockFloorIds.SECOND_FLOOR: 2,
}

MOCK_AREAS: dict[MockAreaIds, dict[str, str | None]] = {
    MockAreaIds.KITCHEN: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.FIRST_FLOOR,
    },
    MockAreaIds.LIVING_ROOM: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.FIRST_FLOOR,
    },
    MockAreaIds.DINING_ROOM: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.FIRST_FLOOR,
    },
    MockAreaIds.MASTER_BEDROOM: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.SECOND_FLOOR,
    },
    MockAreaIds.GUEST_BEDROOM: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.SECOND_FLOOR,
    },
    MockAreaIds.GARAGE: {
        CONF_TYPE: AreaType.INTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.GROUND_LEVEL,
    },
    MockAreaIds.BACKYARD: {
        CONF_TYPE: AreaType.EXTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.GROUND_LEVEL,
    },
    MockAreaIds.FRONT_YARD: {
        CONF_TYPE: AreaType.EXTERIOR,
        ATTR_FLOOR_ID: MockFloorIds.GROUND_LEVEL,
    },
    MockAreaIds.INTERIOR: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: None,
    },
    MockAreaIds.EXTERIOR: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: None,
    },
    MockAreaIds.GLOBAL: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: None,
    },
    MockAreaIds.GROUND_LEVEL: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: MockFloorIds.GROUND_LEVEL,
    },
    MockAreaIds.FIRST_FLOOR: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: MockFloorIds.FIRST_FLOOR,
    },
    MockAreaIds.SECOND_FLOOR: {
        CONF_TYPE: AreaType.META,
        ATTR_FLOOR_ID: MockFloorIds.SECOND_FLOOR,
    },
}

DEFAULT_MOCK_AREA: MockAreaIds = MockAreaIds.KITCHEN
