"""Ampol specific parser."""
import re
import logging
from datetime import datetime
from typing import Optional

from .base_parser import BaseParser

_LOGGER = logging.getLogger(__name__)


class AmpolParser(BaseParser):
    """Parser for Ampol charging receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Ampol"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Check for Ampol domains and email patterns
        ampol_indicators = [
            'ampcharge.com.au',
            'accounts@ampcharge.com.au',
            'ampol.com.au',
            'noreply@ampol.com.au',
            'support@ampcharge.com.au',
            'info@ampcharge.com.au'
        ]
        
        # Check for subject indicators
        subject_indicators = [
            'tax invoice',
            'charging receipt',
            'ev charging',
            'ampcharge',
            'invoice',
            'receipt'
        ]
        
        has_ampol_sender = any(indicator in sender_lower for indicator in ampol_indicators)
        has_relevant_subject = any(indicator in subject_lower for indicator in subject_indicators)
        
        # Also check content for Ampol indicators
        has_ampol_content = any(indicator in sender_lower for indicator in ['ampcharge', 'ampol'])
        
        return has_ampol_sender or (has_ampol_content and has_relevant_subject)
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost using Ampol specific patterns."""
        # Ampol specific cost patterns based on the example
        ampol_patterns = [
            # Primary Ampol patterns from the example
            r'\*\*\$([0-9]+\.[0-9]{2})\*\*\s+for\s+EV\s+charging',  # **$30.72** for EV charging
            r'\*\*Total\s+Cost\*\*[^\d]*\*\*\$([0-9]+\.[0-9]{2})\*\*',  # **Total Cost** **$30.72**
            r'Total\s+Cost[:\s]*\*\*\$([0-9]+\.[0-9]{2})\*\*',  # Total Cost **$30.72**
            r'Total\s+includes[^\$]*\$([0-9]+\.[0-9]{2})',  # Total includes 10% GST of $2.79 (for total extraction)
            
            # Alternative formats
            r'Total[:\s]*\$([0-9]+\.[0-9]{2})',  # Total: $30.72
            r'Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount: $30.72
            r'Cost[:\s]*\$([0-9]+\.[0-9]{2})',  # Cost: $30.72
            r'Charged[:\s]*\$([0-9]+\.[0-9]{2})',  # Charged: $30.72
            
            # Tax invoice patterns
            r'Tax\s+Invoice[^\$]*\$([0-9]+\.[0-9]{2})',  # Tax Invoice ... $30.72
            r'Invoice\s+Total[:\s]*\$([0-9]+\.[0-9]{2})',  # Invoice Total: $30.72
            
            # GST patterns (might capture total)
            r'includes\s+10%\s+GST[^\$]*\$([0-9]+\.[0-9]{2})',  # includes 10% GST of $2.79
            
            # General dollar patterns
            r'\$([0-9]+\.[0-9]{2})\s+for\s+EV',  # $30.72 for EV
            r'EV\s+charging[:\s]*\$([0-9]+\.[0-9]{2})',  # EV charging: $30.72
        ]
        
        for pattern in ampol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    # Skip GST amounts (usually small values like $2.79)
                    if cost_value > 5.0:  # Reasonable minimum for total cost
                        if self.verbose_logging:
                            _LOGGER.debug("Found Ampol cost using pattern '%s': $%.2f", pattern, cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_cost(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location using Ampol specific patterns."""
        # Ampol specific location patterns
        ampol_patterns = [
            # Primary location patterns from the example
            r'Ampol\s+Foodary\s+([A-Za-z\s]+)\s*-\s*[a-z0-9\-]+',  # Ampol Foodary Marsden Park - t184-hu1-3522-025-1
            r'(Ampol\s+Foodary\s+[A-Za-z\s]+)',  # Ampol Foodary Marsden Park
            
            # Address patterns
            r'([A-Za-z\s]+Road\s+\d+,\s+[A-Za-z\s]+\s+\d{4})',  # Richmond Road 875, Marsden Park 2765
            r'(\d+\s+[A-Za-z\s]+Road,\s+[A-Za-z\s]+\s+\d{4})',  # 875 Richmond Road, Marsden Park 2765
            
            # Station/Site patterns
            r'Station[:\s]*([^\n\r]+)',  # Station: ...
            r'Location[:\s]*([^\n\r]+)',  # Location: ...
            r'Site[:\s]*([^\n\r]+)',  # Site: ...
            
            # Charger ID with location
            r'Charger\s+ID[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*\n[^\n]*([A-Za-z\s]+-[a-z0-9\-]+)',  # After charger details
            
            # General address patterns
            r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr)[^\n\r,]*,\s*[A-Za-z\s]+\s*\d{4})',
            r'([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Suburb, STATE 1234
        ]
        
        for pattern in ampol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                
                # Clean up the location
                location = location.replace('\n', ' ').replace('\r', ' ')
                location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
                location = location[:200]  # Limit length
                
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found Ampol location: %s", location)
                    return location
        
        # Fallback to general patterns
        return super().extract_location(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy using Ampol specific patterns."""
        # Ampol specific energy patterns
        ampol_patterns = [
            # Primary energy patterns from the example
            r'Energy\s+Delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Delivered 40.967 kWh
            r'([0-9]+\.[0-9]+)\s*kWh',  # 40.967 kWh
            
            # Alternative formats
            r'Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy: 40.967 kWh
            r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total Energy: 40.967 kWh
            r'kWh\s+Delivered[:\s]*([0-9]+\.[0-9]+)',  # kWh Delivered: 40.967
            r'Delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Delivered: 40.967 kWh
            
            # Session patterns
            r'Session\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Session Energy: 40.967 kWh
            r'Charged[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Charged: 40.967 kWh
        ]
        
        for pattern in ampol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        if self.verbose_logging:
                            _LOGGER.debug("Found Ampol energy: %.2f kWh", energy_value)
                        return energy_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_energy(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration using Ampol specific patterns."""
        # Ampol specific duration patterns
        ampol_patterns = [
            # Primary duration patterns from the example
            r'Duration[:\s]*(\d{2}:\d{2}:\d{2})',  # Duration 00:21:05
            r'Time[:\s]*(\d{2}:\d{2}:\d{2})',  # Time 00:21:05
            
            # Alternative formats
            r'Session\s+Duration[:\s]*(\d{2}:\d{2}:\d{2})',  # Session Duration: 00:21:05
            r'Charging\s+Duration[:\s]*(\d{2}:\d{2}:\d{2})',  # Charging Duration: 00:21:05
            r'Total\s+Time[:\s]*(\d{2}:\d{2}:\d{2})',  # Total Time: 00:21:05
            
            # Time range patterns
            r'Start\s+Time[:\s]*[^\n]*End\s+Time[:\s]*[^\n]*Duration[:\s]*(\d{2}:\d{2}:\d{2})',  # From start/end time section
            
            # Minutes format
            r'Duration[:\s]*(\d+)\s*minutes?',  # Duration: 21 minutes
            r'(\d+)\s*mins?\s*(\d+)?\s*secs?',  # 21 mins 5 secs
        ]
        
        for pattern in ampol_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = match.group(1).strip()
                if self.verbose_logging:
                    _LOGGER.debug("Found Ampol duration: %s", duration)
                return duration
        
        # Fallback to general patterns
        return super().extract_duration(text)
    
    def extract_date(self, text: str):
        """Extract date using Ampol specific patterns."""
        # Ampol specific date patterns
        ampol_date_patterns = [
            # Primary date patterns from the example (Australian format DD/MM/YYYY)
            r'Start\s+Time[:\s]*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',  # Start Time 18/07/2025 09:13 PM
            r'End\s+Time[:\s]*(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',  # End Time 18/07/2025 09:34 PM
            r'(\d{1,2}/\d{1,2}/\d{4})',  # 18/07/2025 (standalone)
            
            # Alternative formats
            r'Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',  # Date: 18/07/2025
            r'Session\s+Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',  # Session Date: 18/07/2025
            r'Invoice\s+Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',  # Invoice Date: 18/07/2025
            
            # With time
            r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2})',  # 18/07/2025 09:13
        ]
        
        # Try Ampol specific patterns first
        for pattern in ampol_date_patterns:
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
                        # Ampol uses Australian format DD/MM/YYYY - use dayfirst=True
                        session_date = pd.to_datetime(date_str, dayfirst=True)
                        if self.verbose_logging:
                            _LOGGER.debug("Found Ampol date: %s -> %s", date_str, session_date)
                        return session_date.to_pydatetime()
                    else:
                        # Fallback without pandas - try to parse DD/MM/YYYY
                        try:
                            session_date = datetime.strptime(date_str, '%d/%m/%Y')
                            return session_date
                        except:
                            # Try other formats
                            for fmt in ['%d/%m/%y', '%m/%d/%Y', '%Y/%m/%d']:
                                try:
                                    session_date = datetime.strptime(date_str, fmt)
                                    return session_date
                                except:
                                    continue
                
                except Exception as e:
                    if self.verbose_logging:
                        _LOGGER.debug("Date parsing failed for '%s': %s", date_str, e)
                    continue
        
        # Fallback to base parser
        return super().extract_date(text)
