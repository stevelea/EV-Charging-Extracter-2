"""
EV Charging Receipt Extractor - Native Home Assistant Integration
"""
import asyncio
import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .ev_processor import EVChargingProcessor
from .data_coordinator import EVChargingDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT]

# Service schemas with slider support
SERVICE_TRIGGER_EXTRACTION_SCHEMA = vol.Schema({
    vol.Optional("email_search_days"): vol.All(vol.Coerce(int), vol.Range(min=1, max=365))
})

SERVICE_DEBUG_EMAIL_PARSING_SCHEMA = vol.Schema({
    vol.Optional("email_search_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=1, max=90))
})

SERVICE_CLEAR_AND_REPROCESS_SCHEMA = vol.Schema({
    vol.Optional("email_search_days", default=30): vol.All(vol.Coerce(int), vol.Range(min=1, max=365))
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up EV Charging Receipt Extractor from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Combine data and options for configuration
    config = {**entry.data, **entry.options}
    
    # Create the processor
    processor = EVChargingProcessor(hass, config)
    
    # Create data coordinator
    coordinator = EVChargingDataCoordinator(hass, processor)
    
    # Store in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "processor": processor,
        "coordinator": coordinator,
    }
    
    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    
    # Load existing data on startup
    await coordinator.async_config_entry_first_refresh()
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup services with enhanced slider support
    await _async_setup_services(hass, processor)
    
    # Schedule automatic updates
    await _async_setup_scheduler(hass, coordinator, config)
    
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    # Combine data and options for new configuration
    new_config = {**entry.data, **entry.options}
    
    # Update the processor configuration
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        processor = hass.data[DOMAIN][entry.entry_id]["processor"]
        processor.update_config(new_config)
        
        # Trigger a refresh to reload with new settings
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove services
    hass.services.async_remove(DOMAIN, "trigger_extraction")
    hass.services.async_remove(DOMAIN, "debug_email_parsing")
    hass.services.async_remove(DOMAIN, "debug_evcc_connection")
    hass.services.async_remove(DOMAIN, "export_to_csv")
    hass.services.async_remove(DOMAIN, "get_database_stats")
    hass.services.async_remove(DOMAIN, "clear_and_reprocess")
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, processor: EVChargingProcessor) -> None:
    """Setup services for the integration with enhanced slider support."""
    
    async def trigger_extraction(call: ServiceCall):
        """Service to trigger manual extraction with optional day override."""
        email_search_days = call.data.get("email_search_days")
        
        _LOGGER.info("Manual extraction triggered with %s days", 
                    email_search_days if email_search_days else "default config")
        
        try:
            # Pass the override days to the processor
            result = await hass.async_add_executor_job(
                processor.process_emails, email_search_days
            )
            
            # Send notification with results
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Charging Extraction Complete",
                    "message": f"Processed {result.get('new_email_receipts', 0)} email receipts and {result.get('new_evcc_sessions', 0)} EVCC sessions.",
                    "notification_id": "ev_extraction_complete"
                }
            )
            
        except Exception as e:
            _LOGGER.error("Error during manual extraction: %s", e)
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Charging Extraction Failed",
                    "message": f"Error: {str(e)}",
                    "notification_id": "ev_extraction_error"
                }
            )
    
    async def debug_email_parsing(call: ServiceCall):
        """Service to debug email parsing with optional day override."""
        email_search_days = call.data.get("email_search_days", 7)
        
        _LOGGER.info("Debug email parsing triggered with %d days", email_search_days)
        
        try:
            await hass.async_add_executor_job(
                processor.debug_email_parsing, email_search_days
            )
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Debug Complete",
                    "message": f"Check the logs for detailed email parsing debug information (searched {email_search_days} days).",
                    "notification_id": "ev_debug_complete"
                }
            )
            
        except Exception as e:
            _LOGGER.error("Error during debug: %s", e)
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Debug Failed",
                    "message": f"Error: {str(e)}",
                    "notification_id": "ev_debug_error"
                }
            )
    
    async def debug_evcc_connection(call: ServiceCall):
        """Service to debug EVCC connection."""
        _LOGGER.info("EVCC debug triggered")
        try:
            await hass.async_add_executor_job(processor.debug_evcc_connection)
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EVCC Debug Complete",
                    "message": "Check the logs for detailed EVCC connection and data information.",
                    "notification_id": "evcc_debug_complete"
                }
            )
            
        except Exception as e:
            _LOGGER.error("Error during EVCC debug: %s", e)
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EVCC Debug Failed",
                    "message": f"Error: {str(e)}",
                    "notification_id": "evcc_debug_error"
                }
            )
    
    async def export_to_csv(call: ServiceCall):
        """Service to export data to CSV."""
        _LOGGER.info("CSV export triggered")
        try:
            await hass.async_add_executor_job(processor.export_to_csv)
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Data Export Complete",
                    "message": "Charging data exported to CSV successfully.",
                    "notification_id": "ev_export_complete"
                }
            )
            
        except Exception as e:
            _LOGGER.error("Error during CSV export: %s", e)
    
    async def get_database_stats(call: ServiceCall):
        """Service to get database statistics."""
        try:
            stats = await hass.async_add_executor_job(processor.get_database_stats)
            
            message = f"""📊 EV Charging Statistics:

Total Sessions: {stats.get('total_receipts', 0)}
Total Cost: ${stats.get('total_cost', 0):.2f}
Total Energy: {stats.get('total_energy', 0):.1f} kWh

Monthly (Last 30 days):
Sessions: {stats.get('monthly_receipts', 0)}
Cost: ${stats.get('monthly_cost', 0):.2f}
Energy: {stats.get('monthly_energy', 0):.1f} kWh

Home vs Public (Monthly):
Home: {stats.get('home_monthly_receipts', 0)} sessions, ${stats.get('home_monthly_cost', 0):.2f}
Public: {stats.get('public_monthly_receipts', 0)} sessions, ${stats.get('public_monthly_cost', 0):.2f}"""
            
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Charging Statistics",
                    "message": message,
                    "notification_id": "ev_stats"
                }
            )
            
        except Exception as e:
            _LOGGER.error("Error getting database stats: %s", e)
    
    async def clear_and_reprocess(call: ServiceCall):
        """Service to clear all data and reprocess with optional day override."""
        email_search_days = call.data.get("email_search_days", 30)
        
        _LOGGER.info("Clear and reprocess triggered with %d days", email_search_days)
        
        try:
            result = await hass.async_add_executor_job(
                processor.clear_data_and_reprocess, email_search_days
            )
            
            if result.get('success'):
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Data Cleared and Reprocessed",
                        "message": f"Cleared {result.get('data_cleared', {}).get('receipts_cleared', 0)} old receipts and found {result.get('new_receipts', 0)} new receipts.",
                        "notification_id": "ev_clear_reprocess_complete"
                    }
                )
            else:
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Clear and Reprocess Failed",
                        "message": f"Error: {result.get('error', 'Unknown error')}",
                        "notification_id": "ev_clear_reprocess_error"
                    }
                )
            
        except Exception as e:
            _LOGGER.error("Error during clear and reprocess: %s", e)
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "EV Clear and Reprocess Failed",
                    "message": f"Error: {str(e)}",
                    "notification_id": "ev_clear_reprocess_error"
                }
            )
    
    # Register services with schemas for slider support
    hass.services.async_register(
        DOMAIN, "trigger_extraction", trigger_extraction, 
        schema=SERVICE_TRIGGER_EXTRACTION_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "debug_email_parsing", debug_email_parsing,
        schema=SERVICE_DEBUG_EMAIL_PARSING_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "debug_evcc_connection", debug_evcc_connection
    )
    hass.services.async_register(
        DOMAIN, "export_to_csv", export_to_csv
    )
    hass.services.async_register(
        DOMAIN, "get_database_stats", get_database_stats
    )
    hass.services.async_register(
        DOMAIN, "clear_and_reprocess", clear_and_reprocess,
        schema=SERVICE_CLEAR_AND_REPROCESS_SCHEMA
    )
    
    _LOGGER.info("🚀 EV Charging services registered with slider controls")


async def _async_setup_scheduler(hass: HomeAssistant, coordinator: EVChargingDataCoordinator, config: dict) -> None:
    """Setup automatic scheduling."""
    if not config.get("schedule_enabled", True):
        return
    
    schedule_hour = config.get("schedule_hour", 2)
    schedule_minute = config.get("schedule_minute", 0)
    
    _LOGGER.info("Setting up daily extraction at %02d:%02d", schedule_hour, schedule_minute)
    
    async def scheduled_update(now):
        """Perform scheduled update."""
        if now.hour == schedule_hour and now.minute == schedule_minute:
            _LOGGER.info("Running scheduled EV charging extraction")
            await coordinator.async_trigger_manual_update()
    
    # Check every minute if it's time for scheduled update
    async_track_time_interval(hass, scheduled_update, timedelta(minutes=1))


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)