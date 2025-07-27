"""Enhanced EV processor with Tesla support - minimal changes to existing code."""
import os
import logging
import imaplib
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from homeassistant.core import HomeAssistant

from .const import (
    CONF_GMAIL_USER, CONF_GMAIL_APP_PASSWORD, CONF_EVCC_URL, CONF_EVCC_ENABLED,
    CONF_HOME_ELECTRICITY_RATE, CONF_DEFAULT_CURRENCY, CONF_DUPLICATE_PREVENTION,
    CONF_VERBOSE_LOGGING, CONF_MINIMUM_COST_THRESHOLD, CONF_EMAIL_SEARCH_DAYS_BACK,
    CONF_AUTO_EXPORT_CSV, DEFAULT_EVCC_URL, DEFAULT_EVCC_ENABLED,
    DEFAULT_HOME_ELECTRICITY_RATE, DEFAULT_CURRENCY, DEFAULT_DUPLICATE_PREVENTION,
    DEFAULT_VERBOSE_LOGGING, DEFAULT_MINIMUM_COST_THRESHOLD,
    DEFAULT_EMAIL_SEARCH_DAYS_BACK, DEFAULT_AUTO_EXPORT_CSV
)

from .processors.database_manager import DatabaseManager
from .processors.email_processor import EmailProcessor
from .processors.evcc_processor import EVCCProcessor
from .utils.export_utils import ExportUtils
from .utils.email_utils import EmailUtils

# Try to import Tesla functionality
try:
    from .processors.tesla_pdf_processor import TeslaPDFProcessor
    TESLA_PDF_AVAILABLE = True
except ImportError:
    TeslaPDFProcessor = None
    TESLA_PDF_AVAILABLE = False

_LOGGER = logging.getLogger(__name__)


class EVChargingProcessor:
    """Main coordinator for EV charging data processing with Tesla support."""

    def __init__(self, hass: HomeAssistant, config: dict):
        """Initialize the processor."""
        self.hass = hass
        self.config = config
        
        # Extract configuration with safe defaults
        self.gmail_user = config.get(CONF_GMAIL_USER, "")
        self.gmail_password = config.get(CONF_GMAIL_APP_PASSWORD, "")
        self.evcc_url = config.get(CONF_EVCC_URL, DEFAULT_EVCC_URL)
        self.evcc_enabled = config.get(CONF_EVCC_ENABLED, DEFAULT_EVCC_ENABLED)
        self.home_electricity_rate = config.get(CONF_HOME_ELECTRICITY_RATE, DEFAULT_HOME_ELECTRICITY_RATE)
        self.default_currency = config.get(CONF_DEFAULT_CURRENCY, DEFAULT_CURRENCY)
        self.duplicate_prevention = config.get(CONF_DUPLICATE_PREVENTION, DEFAULT_DUPLICATE_PREVENTION)
        self.verbose_logging = config.get(CONF_VERBOSE_LOGGING, DEFAULT_VERBOSE_LOGGING)
        self.minimum_cost = config.get(CONF_MINIMUM_COST_THRESHOLD, DEFAULT_MINIMUM_COST_THRESHOLD)
        self.email_search_days = config.get(CONF_EMAIL_SEARCH_DAYS_BACK, DEFAULT_EMAIL_SEARCH_DAYS_BACK)
        self.auto_export_csv = config.get(CONF_AUTO_EXPORT_CSV, DEFAULT_AUTO_EXPORT_CSV)
        
        # Initialize paths
        self.db_path = hass.config.path("ev_charging_data.db")
        self.csv_path = hass.config.path("www", "ev_charging_receipts.csv")
        
        # Ensure www directory exists
        try:
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        except Exception as e:
            _LOGGER.error("Could not create www directory: %s", e)
        
        # Initialize components
        self.database_manager = DatabaseManager(self.db_path)
        
        self.email_processor = EmailProcessor(
            self.gmail_user,
            self.gmail_password,
            self.database_manager,
            self.default_currency,
            self.verbose_logging
        )
        
        self.evcc_processor = EVCCProcessor(
            self.evcc_url,
            self.evcc_enabled,
            self.home_electricity_rate,
            self.database_manager,
            self.default_currency,
            self.verbose_logging
        ) if self.evcc_enabled else None
        
        # Initialize Tesla PDF processor if available
        self.tesla_processor = None
        if TESLA_PDF_AVAILABLE:
            try:
                self.tesla_processor = TeslaPDFProcessor(
                    hass.config.path(),
                    self.database_manager,
                    self.default_currency,
                    self.verbose_logging
                )
                _LOGGER.info("✅ Tesla PDF processor initialized")
            except Exception as e:
                _LOGGER.warning("Could not initialize Tesla PDF processor: %s", e)
        
        self.export_utils = ExportUtils(self.csv_path, self.database_manager)

    def update_config(self, new_config: dict):
        """Update configuration settings."""
        self.gmail_user = new_config.get(CONF_GMAIL_USER, self.gmail_user)
        self.gmail_password = new_config.get(CONF_GMAIL_APP_PASSWORD, self.gmail_password)
        self.evcc_url = new_config.get(CONF_EVCC_URL, self.evcc_url)
        self.evcc_enabled = new_config.get(CONF_EVCC_ENABLED, self.evcc_enabled)
        self.home_electricity_rate = new_config.get(CONF_HOME_ELECTRICITY_RATE, self.home_electricity_rate)
        self.default_currency = new_config.get(CONF_DEFAULT_CURRENCY, self.default_currency)
        self.duplicate_prevention = new_config.get(CONF_DUPLICATE_PREVENTION, self.duplicate_prevention)
        self.verbose_logging = new_config.get(CONF_VERBOSE_LOGGING, self.verbose_logging)
        self.minimum_cost = new_config.get(CONF_MINIMUM_COST_THRESHOLD, self.minimum_cost)
        self.email_search_days = new_config.get(CONF_EMAIL_SEARCH_DAYS_BACK, self.email_search_days)
        self.auto_export_csv = new_config.get(CONF_AUTO_EXPORT_CSV, self.auto_export_csv)
        
        # Update processors with new config
        self.email_processor.gmail_user = self.gmail_user
        self.email_processor.gmail_password = self.gmail_password
        self.email_processor.default_currency = self.default_currency
        self.email_processor.verbose_logging = self.verbose_logging
        
        if self.evcc_processor:
            self.evcc_processor.evcc_url = self.evcc_url
            self.evcc_processor.evcc_enabled = self.evcc_enabled
            self.evcc_processor.home_electricity_rate = self.home_electricity_rate
            self.evcc_processor.default_currency = self.default_currency
            self.evcc_processor.verbose_logging = self.verbose_logging
        
        if self.tesla_processor:
            self.tesla_processor.default_currency = self.default_currency
            self.tesla_processor.verbose_logging = self.verbose_logging
        
        _LOGGER.info("🔄 Configuration updated - EVCC: %s (%s), Tesla: %s, Rate: $%.4f/kWh", 
                    "Enabled" if self.evcc_enabled else "Disabled", 
                    self.evcc_url,
                    "Available" if self.tesla_processor else "Unavailable",
                    self.home_electricity_rate)

    def process_emails(self, override_email_days=None):
        """Main processing function."""
        results = {
            'new_email_receipts': 0,
            'new_tesla_receipts': 0,
            'new_evcc_sessions': 0,
            'errors': []
        }
        
        try:
            # Process emails
            email_days = override_email_days if override_email_days is not None else self.email_search_days
            email_results = self.email_processor.process_emails(email_days)
            results['new_email_receipts'] = email_results.get('new_email_receipts', 0)
            results['errors'].extend(email_results.get('errors', []))
            
            # Process Tesla PDFs from directory (if available)
            if self.tesla_processor:
                try:
                    _LOGGER.info("🚗 Processing Tesla PDFs from directory...")
                    tesla_results = self.tesla_processor.process_tesla_pdfs()
                    results['new_tesla_receipts'] = tesla_results.get('new_tesla_receipts', 0)
                    results['errors'].extend(tesla_results.get('errors', []))
                    
                    _LOGGER.info("✅ Tesla PDF processing complete: %d new receipts", 
                               tesla_results.get('new_tesla_receipts', 0))
                    
                except Exception as e:
                    _LOGGER.error("Error processing Tesla PDFs: %s", e)
                    results['errors'].append(f"Tesla PDF processing error: {str(e)}")
            
            # Process EVCC sessions
            if self.evcc_enabled and self.evcc_processor:
                try:
                    _LOGGER.info("🔌 Processing EVCC sessions...")
                    evcc_results = self.evcc_processor.process_sessions()
                    results['new_evcc_sessions'] = evcc_results.get('new_sessions', 0)
                    results['errors'].extend(evcc_results.get('errors', []))
                    
                    _LOGGER.info("✅ EVCC processing complete: %d new sessions", results['new_evcc_sessions'])
                    
                except Exception as e:
                    _LOGGER.error("Error processing EVCC sessions: %s", e)
                    results['errors'].append(f"EVCC processing error: {str(e)}")
            else:
                if self.verbose_logging:
                    _LOGGER.debug("EVCC processing disabled")
            
            # Auto-export CSV if enabled
            if self.auto_export_csv:
                try:
                    self.export_to_csv()
                except Exception as e:
                    _LOGGER.warning("Failed to auto-export CSV: %s", e)
            
            total_receipts = results['new_email_receipts'] + results['new_tesla_receipts']
            _LOGGER.info("Processing complete: %d email receipts, %d Tesla receipts, %d EVCC sessions", 
                        results['new_email_receipts'], results['new_tesla_receipts'], results['new_evcc_sessions'])
            
        except Exception as e:
            _LOGGER.error("Error in main processing: %s", e)
            results['errors'].append(str(e))
        
        return results

    def process_tesla_pdfs_only(self):
        """Process only Tesla PDFs from directory."""
        if not self.tesla_processor:
            _LOGGER.error("Tesla PDF processor not available")
            return {'new_tesla_receipts': 0, 'errors': ['Tesla PDF processor not available']}
        
        try:
            _LOGGER.info("🚗 Processing Tesla PDFs only...")
            return self.tesla_processor.process_tesla_pdfs()
        except Exception as e:
            _LOGGER.error("Error processing Tesla PDFs only: %s", e)
            return {'new_tesla_receipts': 0, 'errors': [str(e)]}

    def debug_tesla_pdfs(self):
        """Debug Tesla PDF processing."""
        if not self.tesla_processor:
            _LOGGER.error("Tesla PDF processor not available")
            return
        
        try:
            _LOGGER.info("🔍 Debugging Tesla PDFs...")
            self.tesla_processor.debug_tesla_pdfs()
        except Exception as e:
            _LOGGER.error("Error debugging Tesla PDFs: %s", e)

    def clear_data_and_reprocess(self, override_email_days=None):
        """Clear all existing data and reprocess emails from scratch."""
        try:
            _LOGGER.info("🧹 Starting fresh data processing - clearing all existing data")
            
            # Clear all existing data
            clear_result = self.database_manager.clear_all_data()
            
            if not clear_result['success']:
                _LOGGER.error("Failed to clear data: %s", clear_result.get('error', 'Unknown error'))
                return clear_result
            
            _LOGGER.info("✅ Data cleared successfully, now reprocessing emails...")
            
            # Process emails fresh with override days if provided
            process_result = self.process_emails(override_email_days)
            
            # Combine results
            result = {
                'success': True,
                'data_cleared': clear_result,
                'processing_result': process_result,
                'new_email_receipts': process_result['new_email_receipts'],
                'new_tesla_receipts': process_result['new_tesla_receipts'],
                'new_evcc_sessions': process_result['new_evcc_sessions'],
                'errors': process_result['errors']
            }
            
            total_new = (process_result['new_email_receipts'] + 
                        process_result['new_tesla_receipts'] + 
                        process_result['new_evcc_sessions'])
            
            _LOGGER.info("🎉 Fresh processing complete: %d email, %d Tesla, %d EVCC receipts found", 
                        process_result['new_email_receipts'],
                        process_result['new_tesla_receipts'],
                        process_result['new_evcc_sessions'])
            
            return result
            
        except Exception as e:
            _LOGGER.error("Error in clear and reprocess: %s", e)
            return {
                'success': False,
                'error': str(e)
            }

    def get_database_stats(self):
        """Get comprehensive database statistics."""
        return self.database_manager.get_database_stats()

    def export_to_csv(self):
        """Export charging data to CSV."""
        try:
            self.export_utils.export_to_csv()
        except Exception as e:
            _LOGGER.error("Error exporting to CSV: %s", e)

    def clear_all_data(self):
        """Clear all data from database and CSV file."""
        result = self.database_manager.clear_all_data()
        
        # Also clear CSV file
        if result.get('success', False):
            try:
                self.export_utils.clear_csv_file()
                result['csv_cleared'] = True
            except Exception as e:
                _LOGGER.warning("Could not clear CSV file: %s", e)
                result['csv_cleared'] = False
        
        return result

    def debug_email_parsing(self, override_email_days=None):
        """Debug function to help troubleshoot email parsing issues."""
        days = override_email_days if override_email_days is not None else 7
        self.email_processor.debug_email_parsing(days)

    def debug_evcc_connection(self):
        """Debug EVCC connection and data structure."""
        if self.evcc_processor:
            self.evcc_processor.debug_connection()
        else:
            _LOGGER.error("EVCC processor not initialized")

    # Legacy methods for backward compatibility
    def setup_database(self):
        """Legacy method - database is now setup in DatabaseManager."""
        pass

    def extract_pdf_text(self, pdf_data):
        """Legacy method - moved to EmailUtils."""
        return EmailUtils.extract_pdf_text(pdf_data)

    def parse_email_content(self, raw_email):
        """Legacy method - moved to EmailUtils."""
        return EmailUtils.parse_email_content(raw_email, self.verbose_logging)

    def identify_provider(self, sender):
        """Legacy method - moved to ProviderMapping."""
        from .models import ProviderMapping
        return ProviderMapping.identify_provider(sender)

    def generate_receipt_hash(self, receipt, source_type='email'):
        """Legacy method - moved to ChargingReceipt model."""
        return receipt.generate_hash(source_type)

    def is_duplicate_receipt(self, receipt, source_type='email'):
        """Legacy method - moved to DatabaseManager."""
        return self.database_manager.is_duplicate_receipt(receipt, source_type)

    def save_receipt(self, receipt, source_type='email'):
        """Legacy method - moved to DatabaseManager."""
        return self.database_manager.save_receipt(receipt, source_type, self.minimum_cost)

    def connect_to_gmail(self):
        """Legacy method - moved to EmailProcessor."""
        return self.email_processor.connect_to_gmail()

    def get_charging_emails(self, mail, override_days=None):
        """Legacy method - moved to EmailProcessor."""
        days = override_days if override_days is not None else self.email_search_days
        return self.email_processor.get_charging_emails(mail, days)

    def extract_charging_data(self, email_data):
        """Legacy method - now handled by provider-specific parsers."""
        # Find appropriate parser and extract data
        parser = self.email_processor.find_parser(email_data['sender'], email_data['subject'])
        if parser:
            return parser.parse_receipt(email_data)
        return None

    def get_evcc_sessions(self):
        """Legacy method - moved to EVCCProcessor."""
        if self.evcc_processor:
            return self.evcc_processor.get_sessions()
        return []