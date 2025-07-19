"""Sensor platform for EV Charging Extractor with enhanced date formatting."""
import logging
from datetime import datetime, timedelta
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfTime

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # Get the data from hass.data
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data["coordinator"]
    processor = entry_data["processor"]
    
    # Add all sensors
    async_add_entities([
        EVChargingTotalReceiptsSensor(coordinator, processor, config_entry),
        EVChargingTotalCostSensor(coordinator, processor, config_entry),
        EVChargingTotalEnergySensor(coordinator, processor, config_entry),
        EVChargingMonthlyCostSensor(coordinator, processor, config_entry),
        EVChargingMonthlyEnergySensor(coordinator, processor, config_entry),
        EVChargingAverageCostPerKwhSensor(coordinator, processor, config_entry),
        EVChargingLastSessionProviderSensor(coordinator, processor, config_entry),
        EVChargingLastSessionCostSensor(coordinator, processor, config_entry),
        EVChargingLastSessionDateSensor(coordinator, processor, config_entry),
        EVChargingLastSessionEnergySensor(coordinator, processor, config_entry),
        EVChargingTopProviderSensor(coordinator, processor, config_entry),
        EVChargingHomeCostSensor(coordinator, processor, config_entry),
        EVChargingPublicCostSensor(coordinator, processor, config_entry),
    ])


class EVChargingBaseSensor(SensorEntity):
    """Base class for EV charging sensors."""
    
    def __init__(self, coordinator, processor, config_entry, sensor_type):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._processor = processor
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        
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
    
    @property
    def available(self):
        """Return if sensor is available."""
        return self._coordinator.last_update_success
    
    async def async_update(self):
        """Update the sensor."""
        await self._coordinator.async_request_refresh()


class EVChargingTotalReceiptsSensor(EVChargingBaseSensor):
    """Sensor for total number of charging receipts."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "total_receipts")
        self._attr_name = "Total Receipts"
        self._attr_icon = "mdi:receipt"
        self._attr_state_class = SensorStateClass.TOTAL
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        return stats.get('total_receipts', 0)


class EVChargingTotalCostSensor(EVChargingBaseSensor):
    """Sensor for total charging cost."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "total_cost")
        self._attr_name = "Total Cost"
        self._attr_icon = "mdi:currency-usd"
        self._attr_native_unit_of_measurement = "AUD"
        self._attr_state_class = SensorStateClass.TOTAL
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        cost = stats.get('total_cost', 0)
        return round(cost, 2) if cost else 0


class EVChargingTotalEnergySensor(EVChargingBaseSensor):
    """Sensor for total energy consumed."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "total_energy")
        self._attr_name = "Total Energy"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        energy = stats.get('total_energy', 0)
        return round(energy, 2) if energy else 0


class EVChargingMonthlyCostSensor(EVChargingBaseSensor):
    """Sensor for monthly charging cost."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "monthly_cost")
        self._attr_name = "Monthly Cost"
        self._attr_icon = "mdi:calendar-month"
        self._attr_native_unit_of_measurement = "AUD"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        cost = stats.get('monthly_cost', 0)
        return round(cost, 2) if cost else 0


class EVChargingMonthlyEnergySensor(EVChargingBaseSensor):
    """Sensor for monthly energy consumed."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "monthly_energy")
        self._attr_name = "Monthly Energy"
        self._attr_icon = "mdi:calendar-month"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        energy = stats.get('monthly_energy', 0)
        return round(energy, 2) if energy else 0


class EVChargingAverageCostPerKwhSensor(EVChargingBaseSensor):
    """Sensor for average cost per kWh."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "average_cost_per_kwh")
        self._attr_name = "Average Cost per kWh"
        self._attr_icon = "mdi:calculator"
        self._attr_native_unit_of_measurement = "AUD/kWh"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        avg_cost = stats.get('average_cost_per_kwh', 0)
        return round(avg_cost, 4) if avg_cost else 0


class EVChargingLastSessionProviderSensor(EVChargingBaseSensor):
    """Sensor for last session provider."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "last_session_provider")
        self._attr_name = "Last Session Provider"
        self._attr_icon = "mdi:ev-station"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        return stats.get('last_session_provider', 'None')


class EVChargingLastSessionCostSensor(EVChargingBaseSensor):
    """Sensor for last session cost."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "last_session_cost")
        self._attr_name = "Last Session Cost"
        self._attr_icon = "mdi:currency-usd"
        self._attr_native_unit_of_measurement = "AUD"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        cost = stats.get('last_session_cost', 0)
        return round(cost, 2) if cost else 0


class EVChargingLastSessionDateSensor(EVChargingBaseSensor):
    """Sensor for last session date with user-friendly formatting."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "last_session_date")
        self._attr_name = "Last Session Date"
        self._attr_icon = "mdi:clock"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        last_date = stats.get('last_session_date')
        
        if last_date:
            try:
                # Parse the date and format as dd-mm-yy hh:mm
                if isinstance(last_date, str):
                    date_obj = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
                elif isinstance(last_date, datetime):
                    date_obj = last_date
                else:
                    return 'Unknown'
                
                # Format as dd-mm-yy hh:mm in local time
                return date_obj.strftime('%d-%m-%y %H:%M')
            except Exception as e:
                _LOGGER.debug("Error formatting last session date: %s", e)
                return str(last_date)
        
        return 'None'


class EVChargingLastSessionEnergySensor(EVChargingBaseSensor):
    """Sensor for last session energy."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "last_session_energy")
        self._attr_name = "Last Session Energy"
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        energy = stats.get('last_session_energy', 0)
        return round(energy, 2) if energy else 0


class EVChargingTopProviderSensor(EVChargingBaseSensor):
    """Sensor for most used provider."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "top_provider")
        self._attr_name = "Top Provider"
        self._attr_icon = "mdi:trophy"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        return stats.get('top_provider', 'None')


class EVChargingHomeCostSensor(EVChargingBaseSensor):
    """Sensor for monthly home charging cost."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "home_monthly_cost")
        self._attr_name = "Home Charging (Monthly)"
        self._attr_icon = "mdi:home-lightning-bolt"
        self._attr_native_unit_of_measurement = "AUD"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        cost = stats.get('home_monthly_cost', 0)
        return round(cost, 2) if cost else 0


class EVChargingPublicCostSensor(EVChargingBaseSensor):
    """Sensor for monthly public charging cost."""
    
    def __init__(self, coordinator, processor, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator, processor, config_entry, "public_monthly_cost")
        self._attr_name = "Public Charging (Monthly)"
        self._attr_icon = "mdi:ev-station"
        self._attr_native_unit_of_measurement = "AUD"
    
    @property
    def native_value(self):
        """Return the state of the sensor."""
        stats = self._coordinator.data.get('stats', {})
        cost = stats.get('public_monthly_cost', 0)
        return round(cost, 2) if cost else 0