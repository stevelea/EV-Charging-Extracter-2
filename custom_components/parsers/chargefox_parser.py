"""Chargefox specific parser."""
import re
import logging
from datetime import datetime
from typing import Optional

from .base_parser import BaseParser

_LOGGER = logging.getLogger(__name__)


class ChargefoxParser(BaseParser):
    """Parser for Chargefox charging receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Chargefox"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Check for Chargefox domains and email patterns
        chargefox_indicators = [
            'chargefox.com',
            'noreply@chargefox.com',
            'info@chargefox.com',
            'receipts@chargefox.com',
            'support@chargefox.com'
        ]
        
        # Check for subject indicators
        subject_indicators = [
            'charging receipt',
            'payment receipt', 
            'charging session',
            'ev charging',
            'charge complete',
            'invoice',
            'receipt'
        ]
        
        has_chargefox_sender = any(indicator in sender_lower for indicator in chargefox_indicators)
        has_relevant_subject = any(indicator in subject_lower for indicator in subject_indicators)
        
        return has_chargefox_sender and has_relevant_subject
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost using Chargefox specific patterns."""
        # Chargefox specific cost patterns
        chargefox_patterns = [
            # Primary Chargefox patterns
            r'Total\s+Amount\s+including\s+GST[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount including GST $10.46
            r'Payments[:\s]*Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Payments Amount $10.46
            r'Total\s+Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount $10.46
            r'Amount\s+Charged[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount Charged $10.46
            r'Session\s+Cost[:\s]*\$([0-9]+\.[0-9]{2})',  # Session Cost $10.46
            r'Charging\s+Cost[:\s]*\$([0-9]+\.[0-9]{2})',  # Charging Cost $10.46
            
            # Alternative formats
            r'You\s+paid[:\s]*\$([0-9]+\.[0-9]{2})',  # You paid $10.46
            r'Payment[:\s]*\$([0-9]+\.[0-9]{2})',  # Payment $10.46
            r'Total[:\s]*\$([0-9]+\.[0-9]{2})\s+AUD',  # Total $10.46 AUD
            r'AUD\s*\$([0-9]+\.[0-9]{2})',  # AUD $10.46
            
            # Receipt-style patterns
            r'TOTAL[:\s]*\$([0-9]+\.[0-9]{2})',  # TOTAL: $10.46
            r'GST\s+Inclusive[:\s]*\$([0-9]+\.[0-9]{2})',  # GST Inclusive: $10.46
            
            # EV charging specific
            r'EV\s+charging[:\s]*\$([0-9]+\.[0-9]{2})',  # EV charging: $10.46
            r'Charging\s+fee[:\s]*\$([0-9]+\.[0-9]{2})',  # Charging fee: $10.46
        ]
        
        for pattern in chargefox_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    if cost_value > 0:
                        if self.verbose_logging:
                            _LOGGER.debug("Found Chargefox cost using pattern '%s': $%.2f", pattern, cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_cost(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location using Chargefox specific patterns."""
        # Chargefox specific location patterns
        chargefox_patterns = [
            # Primary location patterns
            r'EV\s+charging\s+at\s+([^,\n\r]+,\s*[A-Z]{2,3},?\s*\d{4})\s+on',  # EV charging at location, STATE, 1234 on
            r'charging\s+at\s+([^\n\r]+)\s+on\s+\d{4}',  # charging at location on date
            r'Station[:\s]*([^\n\r]+)',  # Station: location
            r'Location[:\s]*([^\n\r]+)',  # Location: ...
            r'Charging\s+station[:\s]*([^\n\r]+)',  # Charging station: ...
            
            # Address patterns
            r'Address[:\s]*([^\n\r]+)',  # Address: ...
            r'Site[:\s]*([^\n\r]+)',  # Site: ...
            r'Venue[:\s]*([^\n\r]+)',  # Venue: ...
            
            # Specific Chargefox location formats
            r'([A-Za-z\s]+(?:Shopping Centre|Center|Mall|Plaza))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Shopping centers
            r'([A-Za-z\s]+(?:Service Centre|Station))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Service stations
            r'([A-Za-z\s]+(?:Hotel|Motel))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Hotels
            
            # Full address patterns with street numbers
            r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^\n\r,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',
            
            # Suburb/city patterns
            r'([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Suburb, STATE 1234
        ]
        
        for pattern in chargefox_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    # Combine multiple groups for complex patterns
                    location = f"{match.group(1).strip()} {match.group(2).strip()}"
                else:
                    location = match.group(1).strip()
                
                # Clean up the location
                location = location.replace('\n', ' ').replace('\r', ' ')
                location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
                location = location[:200]  # Limit length
                
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found Chargefox location: %s", location)
                    return location
        
        # Fallback to general patterns
        return super().extract_location(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy using Chargefox specific patterns."""
        # Chargefox specific energy patterns
        chargefox_patterns = [
            # Primary energy patterns
            r'Charging\s+for\s+\d+mins?,\s+([0-9]+\.[0-9]+)kWh',  # Charging for 8mins, 16.37kWh
            r'([0-9]+\.[0-9]+)kWh\s+@\s+\$[0-9]+\.[0-9]+/kWh',  # 16.37kWh @ $0.71/kWh
            r'Energy\s+delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy delivered: 16.37 kWh
            r'Total\s+energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total energy: 16.37 kWh
            r'kWh\s+consumed[:\s]*([0-9]+\.[0-9]+)',  # kWh consumed: 16.37
            
            # Alternative formats
            r'([0-9]+\.[0-9]+)\s*kWh\s+delivered',  # 16.37 kWh delivered
            r'([0-9]+\.[0-9]+)\s*kWh\s+charged',  # 16.37 kWh charged
            r'Charged[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Charged: 16.37 kWh
            r'Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy: 16.37 kWh
            
            # Session summary patterns
            r'Session\s+energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Session energy: 16.37 kWh
            r'Power\s+delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Power delivered: 16.37 kWh
            
            # Receipt-style patterns
            r'kWh[:\s]*([0-9]+\.[0-9]+)',  # kWh: 16.37
            r'([0-9]+\.[0-9]+)\s+kilowatt.hours?',  # 16.37 kilowatt hours
        ]
        
        for pattern in chargefox_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        if self.verbose_logging:
                            _LOGGER.debug("Found Chargefox energy: %.2f kWh", energy_value)
                        return energy_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_energy(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration using Chargefox specific patterns."""
        # Chargefox specific duration patterns
        chargefox_patterns = [
            # Primary duration patterns
            r'Charging\s+for\s+(\d+mins?)',  # Charging for 8mins
            r'Session\s+duration[:\s]*(\d+:\d+(?::\d+)?)',  # Session duration: 00:08:30
            r'Duration[:\s]*(\d+:\d+(?::\d+)?)',  # Duration: 00:08:30
            r'Time[:\s]*(\d+:\d+(?::\d+)?)',  # Time: 00:08:30
            
            # Alternative formats
            r'(\d+)\s*minutes?\s+charging',  # 8 minutes charging
            r'(\d+)\s*mins?\s+session',  # 8 mins session
            r'Charged\s+for[:\s]*(\d+)\s*minutes?',  # Charged for: 8 minutes
            r'Session\s+time[:\s]*(\d+)\s*minutes?',  # Session time: 8 minutes
            
            # Hours and minutes
            r'(\d+)\s*hours?\s*(\d+)?\s*minutes?',  # 1 hour 30 minutes
            r'(\d+)h\s*(\d+)?m',  # 1h 30m
            
            # Time range patterns
            r'from\s+\d{1,2}:\d{2}\s+to\s+\d{1,2}:\d{2}',  # from 14:30 to 14:38
            r'Start[:\s]*\d{1,2}:\d{2}[^\n]*End[:\s]*\d{1,2}:\d{2}',  # Start: 14:30 ... End: 14:38
        ]
        
        for pattern in chargefox_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1 and match.group(2):
                    # Handle patterns with hours and minutes
                    hours = match.group(1)
                    minutes = match.group(2)
                    duration = f"{hours}h {minutes}m"
                else:
                    duration = match.group(1).strip()
                
                if self.verbose_logging:
                    _LOGGER.debug("Found Chargefox duration: %s", duration)
                return duration
        
        # Fallback to general patterns
        return super().extract_duration(text)
    
    def extract_date(self, text: str):
        """Extract date using Chargefox specific patterns."""
        # Chargefox often includes dates in specific formats
        chargefox_date_patterns = [
            # Chargefox specific date patterns - IMPORTANT: Handle ISO format correctly
            r'EV\s+charging\s+at[^\n]*on\s+(\d{4}-\d{2}-\d{2})',  # EV charging at ... on 2025-04-11
            r'Date[:\s]*(\d{1,2}\s+[A-Za-z]{3,9},\s+\d{4})',  # Date: 11 April, 2025
            r'Session\s+date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Session date: 11/04/2025
            r'Charged\s+on[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Charged on: April 11, 2025
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+at\s+\d{1,2}:\d{2}',  # 11/04/2025 at 14:30
        ]
        
        # Try Chargefox specific patterns first
        for pattern in chargefox_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).strip()
                    
                    # Import pandas here to avoid circular imports
                    try:
                        import pandas as pd
                    except ImportError:
                        pd = None
                    
                    if pd:
                        # Handle ISO format dates specifically (YYYY-MM-DD)
                        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
                            # This is ISO format (YYYY-MM-DD) - parse correctly
                            session_date = pd.to_datetime(date_str, format='%Y-%m-%d')
                            if self.verbose_logging:
                                _LOGGER.debug("Found Chargefox ISO date: %s -> %s", date_str, session_date)
                            return session_date.to_pydatetime()
                        else:
                            # Use dayfirst=True for Australian DD/MM/YYYY formats
                            session_date = pd.to_datetime(date_str, dayfirst=True)
                            if self.verbose_logging:
                                _LOGGER.debug("Found Chargefox date: %s -> %s", date_str, session_date)
                            return session_date.to_pydatetime()
                    else:
                        # Fallback without pandas
                        try:
                            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
                                # ISO format
                                session_date = datetime.strptime(date_str, '%Y-%m-%d')
                                return session_date
                        except:
                            pass
                
                except Exception as e:
                    if self.verbose_logging:
                        _LOGGER.debug("Date parsing failed for '%s': %s", date_str, e)
                    continue
        
        # Fallback to base parser
        return super().extract_date(text)
