"""Button platform for EV Charging Extractor with input controls."""
import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
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
    """Set up the button platform."""
    # Get the data from hass.data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    processor = entry_data["processor"]
    
    # Add buttons and input controls
    async_add_entities([
        EVChargingRunButton(coordinator, processor, config_entry),
        EVChargingClearDataButton(coordinator, processor, config_entry),
        EVChargingEmailDaysNumber(coordinator, processor, config_entry),
        EVChargingQuickActionSelect(coordinator, processor, config_entry),
        EVChargingProcessWithDaysButton(coordinator, processor, config_entry),
        EVChargingDebugButton(coordinator, processor, config_entry),
    ])


class EVChargingRunButton(ButtonEntity):
    """Button to manually trigger EV charging data extraction."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the button."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_run_now"
        self._attr_name = "Run Now (Default Config)"
        self._attr_icon = "mdi:play-circle"

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

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Run Now button pressed - triggering manual extraction")
        
        try:
            # Use the coordinator's manual trigger method
            await self._coordinator.async_trigger_manual_update()
            _LOGGER.info("Manual extraction completed successfully")
                        
        except Exception as e:
            _LOGGER.error("Error in Run Now button: %s", e)


class EVChargingClearDataButton(ButtonEntity):
    """Button to clear all EV charging data and start fresh."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the button."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_clear_data"
        self._attr_name = "Clear All Data"
        self._attr_icon = "mdi:delete-sweep"

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

    async def async_press(self) -> None:
        """Handle the button press."""
        _LOGGER.info("Clear All Data button pressed - clearing all data and reprocessing")
        
        try:
            # Run the clear and reprocess function
            result = await self._coordinator.hass.async_add_executor_job(
                self._processor.clear_data_and_reprocess
            )
            
            if result.get('success', False):
                _LOGGER.info("✅ Data cleared and reprocessed successfully: %d new receipts", 
                           result.get('new_receipts', 0))
                
                # Trigger coordinator refresh to update sensors
                await self._coordinator.async_request_refresh()
            else:
                _LOGGER.error("❌ Failed to clear and reprocess data: %s", 
                            result.get('error', 'Unknown error'))
                            
        except Exception as e:
            _LOGGER.error("Error in clear data button: %s", e)


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


class EVChargingQuickActionSelect(SelectEntity):
    """Select entity for quick actions with predefined day options."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the select entity."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_quick_action"
        self._attr_name = "Quick Actions"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_entity_category = EntityCategory.CONFIG
        
        # Select options
        self._attr_options = [
            "Select Action...",
            "Process Last 7 Days",
            "Process Last 14 Days", 
            "Process Last 30 Days",
            "Process Last 60 Days",
            "Process Last 90 Days",
            "Debug Last 3 Days",
            "Debug Last 7 Days",
            "Clear & Reprocess 30 Days",
            "Clear & Reprocess 60 Days"
        ]
        self._attr_current_option = "Select Action..."

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

    async def async_select_option(self, option: str) -> None:
        """Handle option selection."""
        self._attr_current_option = option
        self.async_write_ha_state()
        
        # Execute the selected action
        await self._execute_quick_action(option)
        
        # Reset to default after action
        self._attr_current_option = "Select Action..."
        self.async_write_ha_state()

    async def _execute_quick_action(self, option: str) -> None:
        """Execute the selected quick action."""
        try:
            if option.startswith("Process Last"):
                # Extract days from option text
                days_map = {
                    "Process Last 7 Days": 7,
                    "Process Last 14 Days": 14,
                    "Process Last 30 Days": 30,
                    "Process Last 60 Days": 60,
                    "Process Last 90 Days": 90,
                }
                days = days_map.get(option, 30)
                
                _LOGGER.info("Quick action: Processing last %d days", days)
                result = await self._coordinator.hass.async_add_executor_job(
                    self._processor.process_emails, days
                )
                _LOGGER.info("✅ Quick process complete: %d new receipts", 
                           result.get('new_email_receipts', 0))
                
            elif option.startswith("Debug Last"):
                # Extract days from option text
                days_map = {
                    "Debug Last 3 Days": 3,
                    "Debug Last 7 Days": 7,
                }
                days = days_map.get(option, 7)
                
                _LOGGER.info("Quick action: Debug last %d days", days)
                await self._coordinator.hass.async_add_executor_job(
                    self._processor.debug_email_parsing, days
                )
                _LOGGER.info("✅ Debug complete - check logs")
                
            elif option.startswith("Clear & Reprocess"):
                # Extract days from option text
                days_map = {
                    "Clear & Reprocess 30 Days": 30,
                    "Clear & Reprocess 60 Days": 60,
                }
                days = days_map.get(option, 30)
                
                _LOGGER.info("Quick action: Clear and reprocess %d days", days)
                result = await self._coordinator.hass.async_add_executor_job(
                    self._processor.clear_data_and_reprocess, days
                )
                
                if result.get('success'):
                    _LOGGER.info("✅ Clear and reprocess complete: %d new receipts", 
                               result.get('new_receipts', 0))
                    await self._coordinator.async_request_refresh()
                else:
                    _LOGGER.error("❌ Clear and reprocess failed: %s", 
                                result.get('error', 'Unknown error'))
                                
        except Exception as e:
            _LOGGER.error("Error executing quick action '%s': %s", option, e)


class EVChargingProcessWithDaysButton(ButtonEntity):
    """Button to process emails using the custom day setting."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the button."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_process_custom_days"
        self._attr_name = "Process with Custom Days"
        self._attr_icon = "mdi:play-circle-outline"

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

    async def async_press(self) -> None:
        """Handle the button press using custom days."""
        try:
            # Get the email days setting from the number entity
            days_entity_id = f"number.{DOMAIN}_{self._config_entry.entry_id}_email_days"
            days_state = self._coordinator.hass.states.get(days_entity_id)
            
            if days_state:
                days = int(float(days_state.state))
            else:
                days = 30  # Fallback default
            
            _LOGGER.info("Process with Custom Days button pressed - processing %d days", days)
            
            result = await self._coordinator.hass.async_add_executor_job(
                self._processor.process_emails, days
            )
            
            _LOGGER.info("✅ Custom process complete: %d new receipts from %d days", 
                       result.get('new_email_receipts', 0), days)
            
            # Trigger coordinator refresh
            await self._coordinator.async_request_refresh()
                        
        except Exception as e:
            _LOGGER.error("Error in Process with Custom Days button: %s", e)


class EVChargingDebugButton(ButtonEntity):
    """Button to debug email parsing with custom days."""

    def __init__(self, coordinator, processor, config_entry):
        """Initialize the button."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_debug_custom"
        self._attr_name = "Debug with Custom Days"
        self._attr_icon = "mdi:bug"

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

    async def async_press(self) -> None:
        """Handle the button press for debugging."""
        try:
            # Get the email days setting from the number entity
            days_entity_id = f"number.{DOMAIN}_{self._config_entry.entry_id}_email_days"
            days_state = self._coordinator.hass.states.get(days_entity_id)
            
            if days_state:
                days = min(int(float(days_state.state)), 30)  # Limit debug to 30 days max
            else:
                days = 7  # Fallback default
            
            _LOGGER.info("Debug with Custom Days button pressed - debugging %d days", days)
            
            await self._coordinator.hass.async_add_executor_job(
                self._processor.debug_email_parsing, days
            )
            
            _LOGGER.info("✅ Debug complete for %d days - check logs for details", days)
                        
        except Exception as e:
            _LOGGER.error("Error in Debug with Custom Days button: %s", e)