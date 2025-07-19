"""Number platform for EV Charging Extractor."""
import logging
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number platform."""
    # Get the data from hass.data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    processor = entry_data["processor"]
    
    # Add the number entity
    async_add_entities([
        EVChargingEmailDaysNumber(coordinator, processor, config_entry)
    ])


class EVChargingEmailDaysNumber(NumberEntity):
    """Number entity to set email search days."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the number entity."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_email_days"
        self._attr_name = "Email Search Days"
        self._attr_icon = "mdi:calendar-range"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Number entity attributes
        self._attr_native_min_value = 1
        self._attr_native_max_value = 365
        self._attr_native_step = 1
        self._attr_native_value = 30  # Default value
        self._attr_native_unit_of_measurement = "days"
        self._attr_mode = "slider"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "EV Charging Extractor",
            "manufacturer": "Custom Integration",
            "model": "EV Charging Data Processor",
            "sw_version": "1.0",
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        self._attr_native_value = int(value)
        self.async_write_ha_state()
        _LOGGER.debug("Email search days set to: %d", int(value))