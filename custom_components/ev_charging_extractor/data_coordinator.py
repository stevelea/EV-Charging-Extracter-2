"""DataUpdateCoordinator for EV Charging Receipt Extractor - MANUAL ONLY."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EVChargingDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching EV charging data - MANUAL OPERATION ONLY."""

    def __init__(
        self,
        hass: HomeAssistant,
        processor,
    ) -> None:
        """Initialize."""
        self.processor = processor
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # CRITICAL: Set to None to prevent automatic updates
            update_interval=None,
        )
        
        # Track if we should actually process emails
        self._manual_processing_enabled = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data - ONLY updates stats, NO email processing unless manually triggered."""
        try:
            _LOGGER.debug("🔍 Coordinator update called - getting stats only (no email processing)")
            
            # IMPORTANT: Only get database stats, DO NOT process emails
            # This prevents continuous email processing
            stats = await self.hass.async_add_executor_job(
                self.processor.get_database_stats
            )
            
            # Return basic data structure
            data = {
                "stats": stats,
                "last_update": self.hass.loop.time(),
                "last_manual_processing": None,
            }
            
            _LOGGER.debug("✅ Stats updated without email processing")
            return data
            
        except Exception as err:
            _LOGGER.error("❌ Error getting EV stats: %s", err)
            raise UpdateFailed(f"Error getting EV stats: {err}") from err

    async def async_trigger_manual_update(self) -> dict[str, Any]:
        """Trigger a manual update with FULL email processing."""
        _LOGGER.info("🚀 Manual email processing triggered via coordinator")
        
        try:
            # Set flag to indicate manual processing
            self._manual_processing_enabled = True
            
            # Run the actual email processing
            result = await self.hass.async_add_executor_job(
                self.processor.process_emails
            )
            
            # Get updated stats after processing
            stats = await self.hass.async_add_executor_job(
                self.processor.get_database_stats
            )
            
            # Update coordinator data
            self.data = {
                "last_manual_processing": result,
                "stats": stats,
                "last_update": self.hass.loop.time(),
            }
            
            # Reset flag
            self._manual_processing_enabled = False
            
            # Notify listeners of the update
            self.async_update_listeners()
            
            _LOGGER.info("✅ Manual processing complete: %d email, %d Tesla, %d EVCC", 
                        result.get('new_email_receipts', 0),
                        result.get('new_tesla_receipts', 0), 
                        result.get('new_evcc_sessions', 0))
            
            return self.data
            
        except Exception as err:
            self._manual_processing_enabled = False
            _LOGGER.error("❌ Error in manual email processing: %s", err)
            raise UpdateFailed(f"Error in manual email processing: {err}") from err

    async def async_get_database_stats(self) -> dict[str, Any]:
        """Get current database statistics without processing."""
        try:
            _LOGGER.debug("Getting database stats only")
            return await self.hass.async_add_executor_job(
                self.processor.get_database_stats
            )
        except Exception as err:
            _LOGGER.error("Error getting database stats: %s", err)
            return {}

    async def async_export_csv(self) -> bool:
        """Export data to CSV."""
        try:
            await self.hass.async_add_executor_job(
                self.processor.export_to_csv
            )
            return True
        except Exception as err:
            _LOGGER.error("Error exporting CSV: %s", err)
            return False

    async def async_request_refresh(self) -> None:
        """Request a refresh - STATS ONLY, no email processing."""
        _LOGGER.debug("🔄 Refresh requested - updating stats only")
        await super().async_request_refresh()

    async def async_config_entry_first_refresh(self) -> None:
        """Perform first refresh on startup - STATS ONLY."""
        _LOGGER.info("🏁 Initial coordinator setup - getting existing stats")
        
        try:
            # Get initial stats without processing
            stats = await self.hass.async_add_executor_job(
                self.processor.get_database_stats
            )
            
            self.data = {
                "stats": stats,
                "last_update": self.hass.loop.time(),
                "last_manual_processing": None,
            }
            
            # Set as successful
            self.last_update_success = True
            
            _LOGGER.info("✅ Initial setup complete - ready for manual processing")
            
        except Exception as err:
            _LOGGER.error("❌ Error during initial setup: %s", err)
            self.last_update_success = False
            self.data = {
                "stats": {},
                "last_update": self.hass.loop.time(),
                "last_manual_processing": None,
            }