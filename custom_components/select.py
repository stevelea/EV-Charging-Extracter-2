"""Select platform for EV Charging Extractor."""
import logging
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
    """Set up the select platform."""
    # Get the data from hass.data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    processor = entry_data["processor"]
    
    # Add the select entity
    async_add_entities([
        EVChargingQuickActionSelect(coordinator, processor, config_entry)
    ])


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
            "Clear & Reprocess 60 Days",
            "Clear & Reprocess 200 Days"
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
                
                # Send notification
                await self._coordinator.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Quick Action Complete",
                        "message": f"Processed {result.get('new_email_receipts', 0)} receipts from last {days} days.",
                        "notification_id": "ev_quick_action_complete"
                    }
                )
                
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
                
                # Send notification
                await self._coordinator.hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Debug Complete",
                        "message": f"Debug completed for last {days} days. Check logs for details.",
                        "notification_id": "ev_debug_complete"
                    }
                )
                
            elif option.startswith("Clear & Reprocess"):
                # Extract days from option text
                days_map = {
                    "Clear & Reprocess 30 Days": 30,
                    "Clear & Reprocess 60 Days": 60,
                    "Clear & Reprocess 200 Days": 200,
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
                    
                    # Send notification
                    await self._coordinator.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "EV Clear & Reprocess Complete",
                            "message": f"Cleared old data and found {result.get('new_receipts', 0)} receipts from last {days} days.",
                            "notification_id": "ev_clear_reprocess_complete"
                        }
                    )
                else:
                    _LOGGER.error("❌ Clear and reprocess failed: %s", 
                                result.get('error', 'Unknown error'))
                    
                    # Send error notification
                    await self._coordinator.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "EV Clear & Reprocess Failed",
                            "message": f"Error: {result.get('error', 'Unknown error')}",
                            "notification_id": "ev_clear_reprocess_error"
                        }
                    )
                                
        except Exception as e:
            _LOGGER.error("Error executing quick action '%s': %s", option, e)
            
            # Send error notification
            await self._coordinator.hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Quick Action Failed",
                    "message": f"Error executing '{option}': {str(e)}",
                    "notification_id": "ev_quick_action_error"
                }
            )