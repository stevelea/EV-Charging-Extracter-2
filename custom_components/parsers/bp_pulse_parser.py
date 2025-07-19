"""BP Pulse specific parser."""
import re
import logging
from typing import Optional

from .base_parser import BaseParser

_LOGGER = logging.getLogger(__name__)


class BPPulseParser(BaseParser):
    """Parser for BP Pulse charging receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "BP Pulse"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        return any(domain in sender_lower for domain in [
            'bppulse.com.au',
            'bp' # Be careful with this one as it's generic
        ]) and any(keyword in subject.lower() for keyword in [
            'charging', 'receipt', 'session', 'invoice'
        ])
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost using BP Pulse specific patterns."""
        # BP Pulse specific cost patterns
        bp_patterns = [
            r'\*\*Total\s+Cost\*\*[^\d]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',
            r'\*\*Total\s+Sales\s+Amount\*\*[^\d]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',
            r'Total\s+Cost[:\s]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',
            r'Total\s+Sales\s+Amount[:\s]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',
            r'Sale\s+Amount[:\s]*([0-9]+\.[0-9]{2})\s+AUD',
            r'Energy\s+Cost[:\s]*([0-9]+\.[0-9]{2})\s+AUD',
        ]
        
        for pattern in bp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    if cost_value > 0:
                        if self.verbose_logging:
                            _LOGGER.debug("Found BP Pulse cost using pattern '%s': $%.2f", pattern, cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_cost(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location using BP Pulse specific patterns."""
        # BP Pulse specific location patterns
        bp_patterns = [
            r'Location\s+bp\s+pulse\s+([A-Za-z\s]+)\s+([^\n\r]+Drive[^\n\r,]*,\s*[A-Za-z\s]+,?\s*\d{4})',
            r'bp\s+pulse\s+([A-Za-z\s]+)[^\n\r]*([A-Za-z\s]+Drive[^\n\r,]*,\s*[A-Za-z\s]+,?\s*\d{4})',
            r'Location[:\s]*([^\n\r]+bp\s+pulse[^\n\r]+)',
        ]
        
        for pattern in bp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    location = f"{match.group(1).strip()} {match.group(2).strip()}"
                else:
                    location = match.group(1).strip()
                
                location = location[:200]  # Limit length
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found BP Pulse location: %s", location)
                    return location
        
        # Fallback to general patterns
        return super().extract_location(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy using BP Pulse specific patterns."""
        # BP Pulse specific energy patterns
        bp_patterns = [
            r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',
            r'Energy\s+Distributed[:\s]*([0-9]+\.[0-9]+)\s*kWh',
        ]
        
        for pattern in bp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        if self.verbose_logging:
                            _LOGGER.debug("Found BP Pulse energy: %.2f kWh", energy_value)
                        return energy_value
                except (ValueError, IndexError):
                    continue
        
        # Fallback to general patterns
        return super().extract_energy(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration using BP Pulse specific patterns."""
        # BP Pulse specific duration patterns
        bp_patterns = [
            r'Charging\s+Time[:\s]*(\d+)m',
            r'(\d+)m(?:\s*(\d+)s)?',
        ]
        
        for pattern in bp_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                duration = match.group(1).strip()
                if self.verbose_logging:
                    _LOGGER.debug("Found BP Pulse duration: %s", duration)
                return duration
        
        # Fallback to general patterns
        return super().extract_duration(text)