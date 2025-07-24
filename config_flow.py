"""Config flow for EV Charging Receipt Extractor integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import aiohttp
import asyncio

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    CONF_GMAIL_USER,
    CONF_GMAIL_APP_PASSWORD,
    CONF_EVCC_URL,
    CONF_EVCC_ENABLED,
    CONF_HOME_ELECTRICITY_RATE,
    CONF_DEFAULT_CURRENCY,
    CONF_DUPLICATE_PREVENTION,
    CONF_VERBOSE_LOGGING,
    CONF_MINIMUM_COST_THRESHOLD,
    CONF_EMAIL_SEARCH_DAYS_BACK,
    CONF_AUTO_EXPORT_CSV,
    CONF_SCHEDULE_ENABLED,
    CONF_SCHEDULE_HOUR,
    CONF_SCHEDULE_MINUTE,
    DEFAULT_EVCC_URL,
    DEFAULT_EVCC_ENABLED,
    DEFAULT_HOME_ELECTRICITY_RATE,
    DEFAULT_CURRENCY,
    DEFAULT_DUPLICATE_PREVENTION,
    DEFAULT_VERBOSE_LOGGING,
    DEFAULT_MINIMUM_COST_THRESHOLD,
    DEFAULT_EMAIL_SEARCH_DAYS_BACK,
    DEFAULT_AUTO_EXPORT_CSV,
    DEFAULT_SCHEDULE_ENABLED,
    DEFAULT_SCHEDULE_HOUR,
    DEFAULT_SCHEDULE_MINUTE,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GMAIL_USER): str,
        vol.Required(CONF_GMAIL_APP_PASSWORD): str,
        vol.Optional(CONF_EVCC_ENABLED, default=DEFAULT_EVCC_ENABLED): bool,
        vol.Optional(CONF_EVCC_URL, default=DEFAULT_EVCC_URL): str,
        vol.Optional(CONF_HOME_ELECTRICITY_RATE, default=DEFAULT_HOME_ELECTRICITY_RATE): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=2.0)),
        vol.Optional(CONF_DEFAULT_CURRENCY, default=DEFAULT_CURRENCY): str,
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DUPLICATE_PREVENTION, default=DEFAULT_DUPLICATE_PREVENTION): bool,
        vol.Optional(CONF_VERBOSE_LOGGING, default=DEFAULT_VERBOSE_LOGGING): bool,
        vol.Optional(CONF_MINIMUM_COST_THRESHOLD, default=DEFAULT_MINIMUM_COST_THRESHOLD): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=100.0)),
        vol.Optional(CONF_EMAIL_SEARCH_DAYS_BACK, default=DEFAULT_EMAIL_SEARCH_DAYS_BACK): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Optional(CONF_AUTO_EXPORT_CSV, default=DEFAULT_AUTO_EXPORT_CSV): bool,
        vol.Optional(CONF_SCHEDULE_ENABLED, default=DEFAULT_SCHEDULE_ENABLED): bool,
        vol.Optional(CONF_SCHEDULE_HOUR, default=DEFAULT_SCHEDULE_HOUR): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Optional(CONF_SCHEDULE_MINUTE, default=DEFAULT_SCHEDULE_MINUTE): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    
    # Test Gmail connection in executor to avoid blocking
    try:
        import imaplib
        
        def test_gmail_connection():
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(data[CONF_GMAIL_USER], data[CONF_GMAIL_APP_PASSWORD])
            mail.logout()
            return True
        
        await hass.async_add_executor_job(test_gmail_connection)
        _LOGGER.info("Gmail connection test successful")
    except Exception as e:
        _LOGGER.error("Failed to connect to Gmail: %s", e)
        raise InvalidAuth from e
    
    # Test EVCC connection if enabled
    if data.get(CONF_EVCC_ENABLED, False):
        try:
            evcc_url = data.get(CONF_EVCC_URL, DEFAULT_EVCC_URL)
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{evcc_url}/api/state") as response:
                    if response.status == 200:
                        _LOGGER.info("EVCC connection test successful")
                    else:
                        _LOGGER.warning("EVCC connection test failed with status %d, but continuing setup", response.status)
        except Exception as e:
            _LOGGER.warning("Failed to connect to EVCC: %s, but continuing setup", e)
            # Don't fail setup for EVCC issues

    return {"title": f"EV Charging Extractor ({data[CONF_GMAIL_USER]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EV Charging Receipt Extractor."""

    VERSION = 1

    def __init__(self):
        """Initialize."""
        self._user_input = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={
                    "gmail_help": "Use Gmail app password, not regular password",
                    "evcc_help": "Optional: URL to your EVCC installation"
                }
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception as e:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during validation: %s", e)
            errors["base"] = "unknown"
        else:
            # Store user input for next step
            self._user_input.update(user_input)
            
            # Ask if user wants advanced configuration
            return await self.async_step_advanced()

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "gmail_help": "Use Gmail app password, not regular password",
                "evcc_help": "Optional: URL to your EVCC installation"
            }
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle advanced configuration step."""
        if user_input is None:
            return self.async_show_form(
                step_id="advanced",
                data_schema=STEP_ADVANCED_DATA_SCHEMA,
                description_placeholders={
                    "schedule_help": "Daily extraction time (24-hour format)",
                    "threshold_help": "Minimum cost to process receipts",
                    "days_help": "How many days back to search for emails"
                }
            )

        # Combine all input
        combined_input = {**self._user_input, **user_input}
        
        # Check if entry already exists
        await self.async_set_unique_id(combined_input[CONF_GMAIL_USER])
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"EV Charging Extractor ({combined_input[CONF_GMAIL_USER]})",
            data=combined_input,
        )

    async def async_step_import(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for EV Charging Receipt Extractor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update the config entry with new options
            return self.async_create_entry(title="", data=user_input)

        # Get current configuration
        current_config = self.config_entry.data

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_EMAIL_SEARCH_DAYS_BACK,
                    default=current_config.get(CONF_EMAIL_SEARCH_DAYS_BACK, DEFAULT_EMAIL_SEARCH_DAYS_BACK)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
                vol.Optional(
                    CONF_MINIMUM_COST_THRESHOLD,
                    default=current_config.get(CONF_MINIMUM_COST_THRESHOLD, DEFAULT_MINIMUM_COST_THRESHOLD)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=100.0)),
                vol.Optional(
                    CONF_HOME_ELECTRICITY_RATE,
                    default=current_config.get(CONF_HOME_ELECTRICITY_RATE, DEFAULT_HOME_ELECTRICITY_RATE)
                ): vol.All(vol.Coerce(float), vol.Range(min=0.01, max=2.0)),
                vol.Optional(
                    CONF_DUPLICATE_PREVENTION,
                    default=current_config.get(CONF_DUPLICATE_PREVENTION, DEFAULT_DUPLICATE_PREVENTION)
                ): bool,
                vol.Optional(
                    CONF_VERBOSE_LOGGING,
                    default=current_config.get(CONF_VERBOSE_LOGGING, DEFAULT_VERBOSE_LOGGING)
                ): bool,
                vol.Optional(
                    CONF_AUTO_EXPORT_CSV,
                    default=current_config.get(CONF_AUTO_EXPORT_CSV, DEFAULT_AUTO_EXPORT_CSV)
                ): bool,
                vol.Optional(
                    CONF_SCHEDULE_ENABLED,
                    default=current_config.get(CONF_SCHEDULE_ENABLED, DEFAULT_SCHEDULE_ENABLED)
                ): bool,
                vol.Optional(
                    CONF_SCHEDULE_HOUR,
                    default=current_config.get(CONF_SCHEDULE_HOUR, DEFAULT_SCHEDULE_HOUR)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                vol.Optional(
                    CONF_SCHEDULE_MINUTE,
                    default=current_config.get(CONF_SCHEDULE_MINUTE, DEFAULT_SCHEDULE_MINUTE)
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
                vol.Optional(
                    CONF_EVCC_ENABLED,
                    default=current_config.get(CONF_EVCC_ENABLED, DEFAULT_EVCC_ENABLED)
                ): bool,
                vol.Optional(
                    CONF_EVCC_URL,
                    default=current_config.get(CONF_EVCC_URL, DEFAULT_EVCC_URL)
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "days_help": "Number of days back to search for charging emails",
                "threshold_help": "Minimum cost to process receipts (filters out very small charges)",
                "rate_help": "Your home electricity rate per kWh for EVCC cost calculation",
                "schedule_help": "Daily automatic extraction time (24-hour format)"
            }
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""