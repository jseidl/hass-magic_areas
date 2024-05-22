"""The entity selector to use that also allows for nothing to be set."""

from homeassistant.helpers.selector import EntitySelector


class NullableEntitySelector(EntitySelector):
    """Entity selector that can also have a null value."""

    def __call__(self, data: str):
        """Validate the passed selection, if passed."""

        if data in (None, ""):
            return data

        return super().__call__(data)
