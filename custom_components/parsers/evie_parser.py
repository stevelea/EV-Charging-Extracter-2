"""EVIE Networks specific parser."""
import re
import logging
from typing import Optional

from .base_parser import BaseParser

_LOGGER = logging.getLogger(__name__)


class EVIEParser(BaseParser):
    """Parser for EVIE Networks charging receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "EVIE Networks"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        return any(domain in sender_lower for domain in [
            'goevie.com.au',
            'evie'
        ]) and any(keyword in subject.lower() for keyword in [
            'receipt', 'invoice', 'charging session', 'tax invoice'
        ])
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost using EVIE specific patterns."""
        # EVIE specific cost patterns
        evie_patterns = [
            r'\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # **19.54 AUD**
            r'Total\s+Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount: $19.54
            r'Amount\s+Due[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount Due: $19.54
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    if cost_value > 0:
                        if self.verbose_logging:
                            _LOGGER.debug("Found EVIE cost using pattern '%s': $%.2f", pattern, cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_cost(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location using EVIE specific patterns."""
        # EVIE specific location patterns
        evie_patterns = [
            r'Location[:\s]*([^\n\r]+Service Centre[^\n\r]*\d+[^\n\r]*,\s*[A-Z]{2,3}\s*\d{4})',
            r'([A-Za-z\s]+Service Centre)[^\n\r]*(\d+\s+[A-Za-z\s]+(?:Drive|Road|Street|Ave|Avenue)[^\n\r,]*,\s*[A-Z]{2,3}\s*\d{4})',
            r'Station\s+ID[:\s]*[A-Z0-9]+[^\n]*Location[:\s]*([^\n\r]+)',
            r'([A-Za-z\s]+-[A-Za-z\s]+)[^\n\r]*(\d+-?\d*\s+[A-Za-z\s]+(?:Highway|Hwy|Street|St|Road|Rd|Avenue|Ave|Drive|Dr)[^\n\r,]*,\s*[A-Z]{2,3}\s*\d{4})',
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    location = f"{match.group(1).strip()} {match.group(2).strip()}"
                else:
                    location = match.group(1).strip()
                
                location = location[:200]  # Limit length
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found EVIE location: %s", location)
                    return location
        
        # Fallback to general patterns
        return super().extract_location(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy using EVIE specific patterns."""
        # EVIE specific energy patterns
        evie_patterns = [
            r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',
            r'Energy\s+Consumed[:\s]*([0-9]+\.[0-9]+)\s*kWh',
            r'kWh\s+Delivered[:\s]*([0-9]+\.[0-9]+)',
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        if self.verbose_logging:
                            _LOGGER.debug("Found EVIE energy: %.2f kWh", energy_value)
                        return energy_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_energy(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration using EVIE specific patterns."""
        # EVIE specific duration patterns
        evie_patterns = [
            r'Charging\s+Time[:\s]*(\d+)m',
            r'Session\s+Duration[:\s]*(\d+:\d+)',
            r'Duration[:\s]*(\d+\s+minutes?)',
        ]
        
        for pattern in evie_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = match.group(1).strip()
                if self.verbose_logging:
                    _LOGGER.debug("Found EVIE duration: %s", duration)
                return duration
        
        # Fallback to general patterns
        return super().extract_duration(text)
