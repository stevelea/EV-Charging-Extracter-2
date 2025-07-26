"""Constants for the EV Charging Receipt Extractor integration."""
from datetime import timedelta

DOMAIN = "ev_charging_extractor"

# Configuration keys
CONF_GMAIL_USER = "gmail_user"
CONF_GMAIL_APP_PASSWORD = "gmail_app_password"
CONF_EVCC_URL = "evcc_url"
CONF_EVCC_ENABLED = "evcc_enabled"
CONF_HOME_ELECTRICITY_RATE = "home_electricity_rate"
CONF_DEFAULT_CURRENCY = "default_currency"
CONF_DUPLICATE_PREVENTION = "duplicate_prevention"
CONF_VERBOSE_LOGGING = "verbose_logging"
CONF_MINIMUM_COST_THRESHOLD = "minimum_cost_threshold"
CONF_EMAIL_SEARCH_DAYS_BACK = "email_search_days_back"
CONF_AUTO_EXPORT_CSV = "auto_export_csv"
CONF_ENABLE_DB_VACUUM = "enable_db_vacuum"
CONF_INFLUXDB_ENABLED = "influxdb_enabled"
CONF_INFLUXDB_HOST = "influxdb_host"
CONF_INFLUXDB_PORT = "influxdb_port"
CONF_INFLUXDB_DATABASE = "influxdb_database"
CONF_INFLUXDB_USERNAME = "influxdb_username"
CONF_INFLUXDB_PASSWORD = "influxdb_password"
CONF_SCHEDULE_ENABLED = "schedule_enabled"
CONF_SCHEDULE_HOUR = "schedule_hour"
CONF_SCHEDULE_MINUTE = "schedule_minute"

# Default values
DEFAULT_EVCC_URL = "http://homeassistant.local:7070"
DEFAULT_EVCC_ENABLED = True
DEFAULT_HOME_ELECTRICITY_RATE = 0.25
DEFAULT_CURRENCY = "AUD"
DEFAULT_DUPLICATE_PREVENTION = True
DEFAULT_VERBOSE_LOGGING = True
DEFAULT_MINIMUM_COST_THRESHOLD = 0.10
DEFAULT_EMAIL_SEARCH_DAYS_BACK = 30
DEFAULT_AUTO_EXPORT_CSV = True
DEFAULT_ENABLE_DB_VACUUM = True
DEFAULT_INFLUXDB_ENABLED = False
DEFAULT_INFLUXDB_HOST = "homeassistant.local"
DEFAULT_INFLUXDB_PORT = 8086
DEFAULT_INFLUXDB_DATABASE = "ev_charging"
DEFAULT_SCHEDULE_ENABLED = False
DEFAULT_SCHEDULE_HOUR = 2
DEFAULT_SCHEDULE_MINUTE = 0

# Update intervals
DEFAULT_SCAN_INTERVAL = timedelta(hours=6)
MANUAL_UPDATE_INTERVAL = timedelta(minutes=5)

CONF_EMAIL_SEARCH_DAYS_BACK = "email_search_days_back"
DEFAULT_EMAIL_SEARCH_DAYS_BACK = 30  # Default 30 days

# Sensor types
SENSOR_TYPES = {
    "total_sessions": {
        "name": "Total Sessions",
        "icon": "mdi:ev-station",
        "unit_of_measurement": "sessions",
    },
    "total_cost": {
        "name": "Total Cost",
        "icon": "mdi:currency-usd",
        "unit_of_measurement": "AUD",
        "device_class": "monetary",
    },
    "total_energy": {
        "name": "Total Energy",
        "icon": "mdi:lightning-bolt",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
    "monthly_sessions": {
        "name": "Monthly Sessions",
        "icon": "mdi:counter",
        "unit_of_measurement": "sessions",
    },
    "monthly_cost": {
        "name": "Monthly Cost",
        "icon": "mdi:currency-usd",
        "unit_of_measurement": "AUD",
        "device_class": "monetary",
    },
    "monthly_energy": {
        "name": "Monthly Energy",
        "icon": "mdi:lightning-bolt",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
    "home_monthly_sessions": {
        "name": "Home Monthly Sessions",
        "icon": "mdi:home-lightning-bolt",
        "unit_of_measurement": "sessions",
    },
    "home_monthly_cost": {
        "name": "Home Monthly Cost",
        "icon": "mdi:home-currency-usd",
        "unit_of_measurement": "AUD",
        "device_class": "monetary",
    },
    "home_monthly_energy": {
        "name": "Home Monthly Energy",
        "icon": "mdi:home-lightning-bolt",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
    "public_monthly_sessions": {
        "name": "Public Monthly Sessions",
        "icon": "mdi:ev-station",
        "unit_of_measurement": "sessions",
    },
    "public_monthly_cost": {
        "name": "Public Monthly Cost",
        "icon": "mdi:ev-station",
        "unit_of_measurement": "AUD",
        "device_class": "monetary",
    },
    "public_monthly_energy": {
        "name": "Public Monthly Energy",
        "icon": "mdi:ev-station",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
    "average_cost_per_kwh": {
        "name": "Average Cost per kWh",
        "icon": "mdi:calculator",
        "unit_of_measurement": "AUD/kWh",
    },
    "last_session_cost": {
        "name": "Last Session Cost",
        "icon": "mdi:currency-usd",
        "unit_of_measurement": "AUD",
        "device_class": "monetary",
    },
    "last_session_energy": {
        "name": "Last Session Energy",
        "icon": "mdi:lightning-bolt",
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
    "last_session_provider": {
        "name": "Last Session Provider",
        "icon": "mdi:ev-station",
    },
    "top_provider": {
        "name": "Top Provider",
        "icon": "mdi:star",
    },
}

# Australian EV charging providers
EV_PROVIDERS = [
    "Tesla", "ChargePoint", "Chargefox", "EVIE Networks", "EVIE", "Ampol", "BP Pulse",
    "Shell Recharge", "RAC", "RACV", "Tritium", "JET Charge", "Schneider Electric",
    "AGL", "Origin Energy", "Energex", "Ausgrid", "Endeavour Energy",
    "SA Power Networks", "TasNetworks", "Western Power", "Ergon Energy",
    "PowerCor", "CitiPower", "United Energy", "ActewAGL",
    "Plug In", "Engie", "Everty", "ChargeHub", "FuelMe", "NRMA"
]

# Provider email addresses
PROVIDER_EMAILS = [
    "info@chargefox.com", "noreply@chargefox.com", "receipts@chargefox.com",
    "receipt@chargefox.com", "support@chargefox.com",
    "no-reply@goevie.com.au", "noreply@goevie.com.au", "receipts@goevie.com.au",
    "info@goevie.com.au", "support@goevie.com.au",
    "DoNotReply@bppulse.com.au", "noreply@bppulse.com.au", "receipts@bppulse.com.au",
    "support@bppulse.com.au", "info@bppulse.com.au",
    "receipts+acct_190lpFGqJkSbcKDk@stripe.com", "help@exploren.com.au",
    "accounts@ampcharge.com.au", "noreply@ampcharge.com.au", "receipts@ampcharge.com.au",
    "support@ampcharge.com.au", "info@ampcharge.com.au",
    "noreply@tesla.com", "receipts@tesla.com", "billing@tesla.com",
    "noreply@chargepoint.com", "receipts@chargepoint.com",
    "noreply@mynrma.com.au", "receipts@mynrma.com.au", "info@mynrma.com.au"
]