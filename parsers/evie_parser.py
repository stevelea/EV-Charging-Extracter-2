"""Enhanced EVIE Networks specific parser for HTML emails."""
import re
import logging
from datetime import datetime
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from .base_parser import BaseParser

_LOGGER = logging.getLogger(__name__)


class EVIEParser(BaseParser):
    """Enhanced parser for EVIE Networks charging receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "EVIE Networks"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Check for EVIE domains and email patterns
        evie_indicators = [
            'goevie.com.au',
            'evie.com.au', 
            'noreply@evie.com.au',
            'no-reply@goevie.com.au',
            'receipts@goevie.com.au',
            'info@goevie.com.au',
            'support@goevie.com.au'
        ]
        
        # Check for subject indicators
        subject_indicators = [
            'evie networks receipt',
            'your evie networks receipt',
            'receipt',
            'invoice', 
            'charging session',
            'tax invoice',
            'payment confirmation'
        ]
        
        has_evie_sender = any(indicator in sender_lower for indicator in evie_indicators)
        has_relevant_subject = any(indicator in subject_lower for indicator in subject_indicators)
        
        return has_evie_sender and has_relevant_subject
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost using EVIE specific patterns optimized for HTML content."""
        # Enhanced EVIE specific cost patterns for HTML content
        evie_patterns = [
            # Primary EVIE patterns from HTML
            r'Total\s+Amount[:\s]*\$?([0-9]+\.[0-9]{2})',  # Total Amount: $19.54
            r'Amount\s+Due[:\s]*\$?([0-9]+\.[0-9]{2})',  # Amount Due: $19.54
            r'Final\s+Amount[:\s]*\$?([0-9]+\.[0-9]{2})',  # Final Amount: $19.54
            r'Total[:\s]*\$?([0-9]+\.[0-9]{2})',  # Total: $19.54
            
            # HTML table patterns
            r'<td[^>]*>\s*Total\s*</td>\s*<td[^>]*>\s*\$?([0-9]+\.[0-9]{2})',  # HTML table cells
            r'<td[^>]*>\s*Amount\s*</td>\s*<td[^>]*>\s*\$?([0-9]+\.[0-9]{2})',
            
            # Bold/emphasis patterns from HTML
            r'<(?:b|strong)[^>]*>\s*\$?([0-9]+\.[0-9]{2})\s*</(?:b|strong)>.*(?:AUD|Total|Amount)',
            r'(?:Total|Amount)[^0-9]*<(?:b|strong)[^>]*>\s*\$?([0-9]+\.[0-9]{2})',
            
            # Currency patterns
            r'\$([0-9]+\.[0-9]{2})\s+AUD',  # $19.54 AUD
            r'([0-9]+\.[0-9]{2})\s*AUD',  # 19.54 AUD
            r'AUD\s*\$?([0-9]+\.[0-9]{2})',  # AUD $19.54
            
            # Payment confirmation patterns
            r'Payment\s+of\s+\$?([0-9]+\.[0-9]{2})',  # Payment of $19.54
            r'Charged\s+\$?([0-9]+\.[0-9]{2})',  # Charged $19.54
            r'You\s+paid\s+\$?([0-9]+\.[0-9]{2})',  # You paid $19.54
            
            # Invoice patterns
            r'Invoice\s+Total[:\s]*\$?([0-9]+\.[0-9]{2})',  # Invoice Total: $19.54
            r'Tax\s+Invoice[^0-9]*\$?([0-9]+\.[0-9]{2})',  # Tax Invoice ... $19.54
            
            # Session cost patterns
            r'Session\s+Cost[:\s]*\$?([0-9]+\.[0-9]{2})',  # Session Cost: $19.54
            r'Charging\s+Cost[:\s]*\$?([0-9]+\.[0-9]{2})',  # Charging Cost: $19.54
            r'Energy\s+Cost[:\s]*\$?([0-9]+\.[0-9]{2})',  # Energy Cost: $19.54
            
            # Generic dollar patterns (use as last resort)
            r'\$([0-9]+\.[0-9]{2})(?!\s*(?:kWh|/kWh|per))',  # $19.54 (but not per kWh)
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    cost_value = float(match.group(1))
                    # Validate cost is reasonable (not a rate or small fee)
                    if 1.0 <= cost_value <= 500.0:  # Reasonable range for charging session
                        if self.verbose_logging:
                            _LOGGER.debug("Found EVIE cost using pattern '%s': $%.2f", pattern, cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_cost(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location using EVIE specific patterns optimized for HTML content."""
        # Enhanced EVIE specific location patterns
        evie_patterns = [
            # Service center patterns
            r'([A-Za-z\s]+Service\s+Centre)[^<\n]*([0-9-]+\s+[A-Za-z\s]+(?:Drive|Road|Street|Ave|Avenue|Highway|Hwy)[^<\n,]*,\s*[A-Z]{2,3}\s*[0-9]{4})',
            r'Location[:\s]*([^<\n]+Service\s+Centre[^<\n]*[0-9]+[^<\n]*,\s*[A-Z]{2,3}\s*[0-9]{4})',
            
            # Station ID with location
            r'Station\s+ID[:\s]*[A-Z0-9]+[^<\n]*Location[:\s]*([^<\n]+)',
            r'Station[:\s]*([^<\n]+)',  # Station: location
            
            # HTML table location patterns
            r'<td[^>]*>\s*(?:Location|Site|Station)\s*</td>\s*<td[^>]*>\s*([^<]+)',
            r'<td[^>]*>\s*([^<]+Service\s+Centre[^<]*)</td>',
            
            # Address patterns from HTML
            r'([A-Za-z\s]+-[A-Za-z\s]+)[^<\n]*([0-9-]+\s+[A-Za-z\s]+(?:Highway|Hwy|Street|St|Road|Rd|Avenue|Ave|Drive|Dr)[^<\n,]*,\s*[A-Z]{2,3}\s*[0-9]{4})',
            
            # General location patterns
            r'Location[:\s]*([^<\n\r]+)',  # Location: ...
            r'Site[:\s]*([^<\n\r]+)',  # Site: ...
            r'Address[:\s]*([^<\n\r]+)',  # Address: ...
            r'Charging\s+(?:at|station)[:\s]*([^<\n\r]+)',  # Charging at: ...
            
            # Full address patterns
            r'([0-9-]+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^<\n,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2,3}\s*[0-9]{4})',
            r'([A-Za-z\s]+,\s*[A-Z]{2,3}\s*[0-9]{4})',  # Suburb, STATE 1234
            
            # Service center without full address
            r'([A-Za-z\s]+Service\s+Centre)',  # Just the service center name
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if len(match.groups()) > 1:
                    # Combine multiple groups for full location
                    location_parts = [group.strip() for group in match.groups() if group and group.strip()]
                    location = ', '.join(location_parts)
                else:
                    location = match.group(1).strip()
                
                # Clean up the location
                location = re.sub(r'<[^>]+>', '', location)  # Remove any HTML tags
                location = location.replace('\n', ' ').replace('\r', ' ')
                location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
                location = location[:200]  # Limit length
                
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found EVIE location: %s", location)
                    return location
        
        # Fallback to general patterns
        return super().extract_location(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy using EVIE specific patterns optimized for HTML content."""
        # Enhanced EVIE specific energy patterns
        evie_patterns = [
            # Primary EVIE energy patterns
            r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total Energy: 26.4047 kWh
            r'Energy\s+Consumed[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Consumed: 26.4047 kWh
            r'Energy\s+Delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Delivered: 26.4047 kWh
            r'kWh\s+Delivered[:\s]*([0-9]+\.[0-9]+)',  # kWh Delivered: 26.4047
            r'Session\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Session Energy: 26.4047 kWh
            
            # HTML table patterns
            r'<td[^>]*>\s*(?:Energy|kWh)\s*</td>\s*<td[^>]*>\s*([0-9]+\.[0-9]+)',
            r'<td[^>]*>\s*([0-9]+\.[0-9]+)\s*kWh\s*</td>',
            
            # General energy patterns with context
            r'([0-9]+\.[0-9]+)\s*kWh\s*(?:delivered|consumed|charged)',  # X.X kWh delivered
            r'(?:Charged|Delivered)[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Charged: X.X kWh
            
            # Energy with pricing context (to distinguish from rates)
            r'([0-9]+\.[0-9]+)\s*kWh\s*@\s*\$[0-9]+\.[0-9]+',  # X.X kWh @ $0.XX
            r'([0-9]+\.[0-9]+)\s*kWh\s*(?:for|total)',  # X.X kWh for/total
            
            # Standard patterns (be more specific for EVIE)
            r'([0-9]+\.[0-9]{3,4})\s*kWh',  # Match longer decimal precision typical of EVIE
            r'(\d+\.\d+)\s*kWh(?!\s*(?:rate|per|@|\$))',  # kWh not followed by rate indicators
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    energy_value = float(match.group(1))
                    # Validate reasonable energy range
                    if 0.1 < energy_value < 200:  # Reasonable range for charging session
                        # Additional validation: ensure it's not a rate (rates are usually < 1.0)
                        if energy_value >= 1.0 or energy_value > 0.5:  # Most sessions > 0.5 kWh
                            if self.verbose_logging:
                                _LOGGER.debug("Found EVIE energy: %.4f kWh using pattern: %s", energy_value, pattern)
                            return energy_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_energy(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration using EVIE specific patterns optimized for HTML content."""
        # Enhanced EVIE specific duration patterns
        evie_patterns = [
            # Primary EVIE duration patterns
            r'Charging\s+Time[:\s]*(\d+)m(?:in(?:ute)?s?)?',  # Charging Time: 13m
            r'Session\s+Duration[:\s]*(\d+:\d+(?::\d+)?)',  # Session Duration: 00:13:45
            r'Duration[:\s]*(\d+\s+minutes?)',  # Duration: 13 minutes
            r'Total\s+Time[:\s]*(\d+:\d+(?::\d+)?)',  # Total Time: 00:13:45
            
            # HTML table patterns
            r'<td[^>]*>\s*(?:Duration|Time)\s*</td>\s*<td[^>]*>\s*(\d+:\d+(?::\d+)?)',
            r'<td[^>]*>\s*(\d+\s*(?:minutes?|mins?|hours?))\s*</td>',
            
            # Time format patterns
            r'(\d{2}:\d{2}:\d{2})',  # HH:MM:SS
            r'(\d{1,2}:\d{2})',  # H:MM or HH:MM
            
            # Minutes format
            r'(\d+)\s*(?:minutes?|mins?|m)(?!\s*(?:ago|before|after))',  # X minutes (not relative time)
            r'Session\s+(?:time|length)[:\s]*(\d+)\s*(?:minutes?|mins?)',  # Session time: X minutes
            
            # Hours and minutes combined
            r'(\d+)\s*(?:hours?|hrs?|h)\s*(?:and\s*)?(\d+)?\s*(?:minutes?|mins?|m)?',  # X hours Y minutes
            r'(\d+)h\s*(\d+)?m',  # Xh Ym format
            
            # Session timing
            r'Started[^<\n]*?(\d{1,2}:\d{2}).*?(?:Ended|Finished)[^<\n]*?(\d{1,2}:\d{2})',  # Start and end times
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                if len(match.groups()) > 1 and match.group(2):
                    # Handle patterns with hours and minutes
                    hours = match.group(1)
                    minutes = match.group(2)
                    if minutes:
                        duration = f"{hours}h {minutes}m"
                    else:
                        duration = f"{hours}h"
                else:
                    duration = match.group(1).strip()
                
                # Clean HTML from duration
                duration = re.sub(r'<[^>]+>', '', duration)
                
                if self.verbose_logging:
                    _LOGGER.debug("Found EVIE duration: %s using pattern: %s", duration, pattern)
                return duration
        
        # Fallback to general patterns
        return super().extract_duration(text)
    
    def extract_date(self, text: str):
        """Extract date using EVIE specific patterns optimized for HTML content."""
        # Enhanced EVIE specific date patterns
        evie_date_patterns = [
            # EVIE typical patterns from HTML emails
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*[A-Z]{3,4})',  # July 4, 2025 at 7:54:13 PM AEST
            r'Session\s+Date[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Session Date: July 4, 2025
            r'Charging\s+Date[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Charging Date: July 4, 2025
            
            # HTML table date patterns
            r'<td[^>]*>\s*(?:Date|Session Date)\s*</td>\s*<td[^>]*>\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            r'<td[^>]*>\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s*</td>',
            
            # Alternative date formats
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+at\s+(\d{1,2}:\d{2})',  # DD/MM/YYYY at HH:MM
            r'(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})',  # YYYY-MM-DD HH:MM
            
            # Receipt/Invoice date patterns
            r'Receipt\s+Date[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Receipt Date: July 4, 2025
            r'Invoice\s+Date[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Invoice Date: July 4, 2025
            r'Tax\s+Invoice[^<\n]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Tax Invoice ... July 4, 2025
            
            # Date in email headers or timestamps
            r'Date[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Date: July 4, 2025
            
            # Standalone date patterns
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # July 4, 2025
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # DD/MM/YYYY or MM/DD/YYYY
            r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
        ]
        
        # Try EVIE specific patterns first
        for pattern in evie_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    date_str = match.group(1).strip()
                    
                    # Clean HTML from date string
                    date_str = re.sub(r'<[^>]+>', '', date_str)
                    
                    # Parse the date
                    if pd:
                        try:
                            # For EVIE, expect formats like "July 4, 2025" or "04/07/2025"
                            if re.match(r'^[A-Za-z]', date_str):
                                # Month name format (July 4, 2025)
                                session_date = pd.to_datetime(date_str, errors='coerce')
                            else:
                                # Numeric format - try Australian format first (DD/MM/YYYY)
                                session_date = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                            
                            if pd.notna(session_date):
                                if self.verbose_logging:
                                    _LOGGER.debug("Found EVIE date: %s -> %s", date_str, session_date)
                                return session_date.to_pydatetime()
                        except:
                            pass
                    
                    # Fallback manual parsing
                    try:
                        # Try common formats
                        formats = [
                            '%B %d, %Y',  # July 4, 2025
                            '%b %d, %Y',   # Jul 4, 2025
                            '%d/%m/%Y',    # 04/07/2025 (Australian)
                            '%m/%d/%Y',    # 07/04/2025 (US)
                            '%Y-%m-%d',    # 2025-07-04
                        ]
                        
                        for fmt in formats:
                            try:
                                session_date = datetime.strptime(date_str, fmt)
                                if self.verbose_logging:
                                    _LOGGER.debug("Found EVIE date with format %s: %s -> %s", fmt, date_str, session_date)
                                return session_date
                            except ValueError:
                                continue
                    except:
                        pass
                
                except Exception as e:
                    if self.verbose_logging:
                        _LOGGER.debug("Date parsing failed for '%s': %s", date_str, e)
                    continue
        
        # Fallback to base parser
        return super().extract_date(text)