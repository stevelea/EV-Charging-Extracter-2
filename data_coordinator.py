"""DataUpdateCoordinator for EV Charging Receipt Extractor."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class EVChargingDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching EV charging data."""

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
            update_interval=None,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            _LOGGER.debug("Updating EV charging data")
            
            # Run the processor in executor to avoid blocking
            result = await self.hass.async_add_executor_job(
                self.processor.process_emails
            )
            
            # Get current database statistics
            stats = await self.hass.async_add_executor_job(
                self.processor.get_database_stats
            )
            
            # Combine results
            data = {
                "last_update_result": result,
                "stats": stats,
                "last_update": self.hass.loop.time(),
            }
            
            _LOGGER.debug("EV charging data updated successfully")
            return data
            
        except Exception as err:
            _LOGGER.error("Error communicating with EV processor: %s", err)
            raise UpdateFailed(f"Error communicating with EV processor: {err}") from err

    async def async_trigger_manual_update(self) -> dict[str, Any]:
        """Trigger a manual update."""
        _LOGGER.info("Manual update triggered")
        await self.async_request_refresh()
        return self.data or {}

    async def async_get_database_stats(self) -> dict[str, Any]:
        """Get current database statistics."""
        try:
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