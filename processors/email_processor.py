"""Email processor for EV charging receipts with fixed imports."""
import imaplib
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..models import ProviderMapping
from ..utils.email_utils import EmailUtils  # Fixed import
from ..parsers import BPPulseParser, EVIEParser, ChargefoxParser, AmpolParser
from .database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class EmailProcessor:
    """Handles email fetching and processing for EV charging receipts."""
    
    def __init__(self, gmail_user: str, gmail_password: str, database_manager: DatabaseManager, 
                 default_currency: str = "AUD", verbose_logging: bool = False):
        """Initialize email processor."""
        self.gmail_user = gmail_user
        self.gmail_password = gmail_password
        self.database_manager = database_manager
        self.default_currency = default_currency
        self.verbose_logging = verbose_logging
        
        # Initialize parsers
        self.parsers = [
            BPPulseParser(default_currency, verbose_logging),
            EVIEParser(default_currency, verbose_logging),
            ChargefoxParser(default_currency, verbose_logging),
            AmpolParser(default_currency, verbose_logging),
            # Add more parsers here as needed
        ]
    
    def connect_to_gmail(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to Gmail via IMAP."""
        try:
            if not self.gmail_user or not self.gmail_password:
                _LOGGER.error("Gmail credentials not configured")
                return None
                
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.gmail_user, self.gmail_password)
            return mail
        except Exception as e:
            _LOGGER.error("Error connecting to Gmail: %s", e)
            return None
    
    def get_charging_emails(self, mail: imaplib.IMAP4_SSL, days_back: int = 30) -> List[bytes]:
        """Fetch emails from charging providers."""
        try:
            mail.select('inbox')
            
            date_since = (datetime.now() - timedelta(days=days_back)).strftime("%d-%b-%Y")
            
            if self.verbose_logging:
                _LOGGER.info("Searching emails since %s (%d days back)", date_since, days_back)
            
            all_emails = []
            search_terms = ProviderMapping.get_search_terms()
            
            for term in search_terms:
                try:
                    search_criteria = f'({term} SINCE {date_since})'
                    result, data = mail.search(None, search_criteria)
                    
                    if result == 'OK' and data[0]:
                        email_ids = data[0].split()
                        if len(email_ids) > 0 and self.verbose_logging:
                            _LOGGER.debug("Found %d emails from search: %s", len(email_ids), term)
                        
                        for email_id in email_ids[:10]:  # Limit emails per search
                            result, msg_data = mail.fetch(email_id, '(RFC822)')
                            if result == 'OK':
                                all_emails.append(msg_data[0][1])
                                
                except Exception as e:
                    if self.verbose_logging:
                        _LOGGER.warning("Error with search '%s': %s", term, e)
            
            # Remove duplicates
            unique_emails = []
            seen_ids = set()
            
            for email_bytes in all_emails:
                email_hash = hashlib.sha256(email_bytes).hexdigest()
                if email_hash not in seen_ids:
                    seen_ids.add(email_hash)
                    unique_emails.append(email_bytes)
            
            _LOGGER.info("Found %d unique charging emails", len(unique_emails))
            return unique_emails
            
        except Exception as e:
            _LOGGER.error("Error getting charging emails: %s", e)
            return []
    
    def process_emails(self, days_back: int = 30) -> Dict[str, int]:
        """Process charging emails and extract receipts."""
        results = {
            'new_email_receipts': 0,
            'errors': []
        }
        
        try:
            mail = self.connect_to_gmail()
            if not mail:
                return results
            
            emails = self.get_charging_emails(mail, days_back)
            
            for i, raw_email in enumerate(emails):
                try:
                    # Check if email already processed
                    email_hash = hashlib.sha256(raw_email).hexdigest()
                    if self.database_manager.is_email_processed(email_hash):
                        if self.verbose_logging:
                            _LOGGER.debug("Skipping already processed email %d", i+1)
                        continue
                    
                    # Parse email content
                    email_data = EmailUtils.parse_email_content(raw_email, self.verbose_logging)
                    
                    if self.verbose_logging:
                        _LOGGER.info("Processing email %d/%d from %s", 
                                   i+1, len(emails), email_data['sender'])
                    
                    # Find appropriate parser
                    parser = self.find_parser(email_data['sender'], email_data['subject'])
                    
                    if parser:
                        receipt = parser.parse_receipt(email_data)
                        
                        if receipt:
                            if self.database_manager.save_receipt(receipt, 'email'):
                                results['new_email_receipts'] += 1
                                _LOGGER.info("Successfully processed email from %s: $%.2f", 
                                           email_data['sender'], receipt.cost)
                                
                                # Mark email as processed
                                self.database_manager.mark_email_processed(
                                    email_hash, email_data['subject']
                                )
                        else:
                            if self.verbose_logging:
                                _LOGGER.debug("No receipt data extracted from email %d", i+1)
                    else:
                        if self.verbose_logging:
                            _LOGGER.debug("No parser found for email from %s", email_data['sender'])
                        
                        # Mark as processed even if no parser found to avoid reprocessing
                        self.database_manager.mark_email_processed(
                            email_hash, email_data['subject']
                        )
                    
                except Exception as e:
                    _LOGGER.error("Error processing email %d: %s", i+1, e)
                    results['errors'].append(str(e))
            
            mail.logout()
            
        except Exception as e:
            _LOGGER.error("Error in email processing: %s", e)
            results['errors'].append(str(e))
        
        return results
    
    def find_parser(self, sender: str, subject: str) -> Optional[object]:
        """Find appropriate parser for the email."""
        for parser in self.parsers:
            if parser.can_parse(sender, subject):
                return parser
        return None
    
    def debug_email_parsing(self, days_back: int = 7):
        """Debug function to help troubleshoot email parsing issues."""
        try:
            mail = self.connect_to_gmail()
            if not mail:
                _LOGGER.error("Could not connect to Gmail for debugging")
                return
            
            emails = self.get_charging_emails(mail, days_back)
            _LOGGER.info("Found %d emails for debugging", len(emails))
            
            for i, raw_email in enumerate(emails[:3]):  # Debug first 3 emails
                try:
                    email_data = EmailUtils.parse_email_content(raw_email, True)
                    _LOGGER.info("=== DEBUG EMAIL %d ===", i+1)
                    _LOGGER.info("Subject: %s", email_data['subject'])
                    _LOGGER.info("Sender: %s", email_data['sender'])
                    _LOGGER.info("Has PDF: %s", email_data.get('has_pdf', False))
                    _LOGGER.info("Text content preview: %s", email_data['text_content'][:1000])
                    
                    # Find parser and try to extract data
                    parser = self.find_parser(email_data['sender'], email_data['subject'])
                    if parser:
                        _LOGGER.info("Found parser: %s", parser.__class__.__name__)
                        receipt = parser.parse_receipt(email_data)
                        if receipt:
                            _LOGGER.info("Successfully extracted receipt: %s", receipt)
                        else:
                            _LOGGER.info("Could not extract receipt data from this email")
                    else:
                        _LOGGER.info("No parser found for this email")
                    
                except Exception as e:
                    _LOGGER.error("Error debugging email %d: %s", i+1, e)
            
            mail.logout()
            
        except Exception as e:
            _LOGGER.error("Error in debug function: %s", e)