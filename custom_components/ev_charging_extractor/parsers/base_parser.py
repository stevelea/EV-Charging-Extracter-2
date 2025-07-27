"""Base parser class for EV charging providers with fixed imports."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from ..models import ChargingReceipt

_LOGGER = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for provider-specific parsers."""
    
    def __init__(self, default_currency: str = "AUD", verbose_logging: bool = False):
        """Initialize base parser."""
        self.default_currency = default_currency
        self.verbose_logging = verbose_logging
        self.provider_name = self.get_provider_name()
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @abstractmethod
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        pass
    
    def parse_receipt(self, email_data: Dict[str, any]) -> Optional[ChargingReceipt]:
        """Parse email data into a charging receipt."""
        try:
            text = email_data['text_content']
            subject = email_data['subject']
            sender = email_data['sender']
            
            if not text.strip():
                if self.verbose_logging:
                    _LOGGER.debug("Skipping email - no text content found")
                return None
            
            # Extract data using provider-specific methods
            cost = self.extract_cost(text)
            if not cost or cost <= 0:
                if self.verbose_logging:
                    _LOGGER.debug("No valid cost found for %s email", self.provider_name)
                return None
            
            # Extract other fields
            session_date = self.extract_date(text)
            location = self.extract_location(text)
            energy_kwh = self.extract_energy(text)
            session_duration = self.extract_duration(text)
            
            if self.verbose_logging:
                _LOGGER.debug("Extracted data - Provider: %s, Cost: %.2f, Location: %s, Energy: %s kWh", 
                            self.provider_name, cost, location, energy_kwh)
            
            # Create receipt
            receipt = ChargingReceipt(
                provider=self.provider_name,
                date=session_date,
                location=location or "Unknown",
                cost=cost,
                currency=self.default_currency,
                energy_kwh=energy_kwh,
                session_duration=session_duration,
                email_subject=subject,
                raw_data=text[:2000]  # Store first 2000 chars for debugging
            )
            
            return receipt
            
        except Exception as e:
            _LOGGER.error("Error parsing %s receipt: %s", self.provider_name, e)
            return None
    
    def extract_cost(self, text: str) -> Optional[float]:
        """Extract cost from text. Can be overridden by subclasses."""
        try:
            from ..utils import PatternUtils
            return PatternUtils.extract_cost(text)
        except ImportError:
            # Fallback cost extraction
            import re
            patterns = [
                r'Total[:\s]*\$([0-9]+\.[0-9]{2})',
                r'Amount[:\s]*\$([0-9]+\.[0-9]{2})',
                r'\$([0-9]+\.[0-9]{2})',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except:
                        continue
            return None
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy from text. Can be overridden by subclasses."""
        try:
            from ..utils import PatternUtils
            return PatternUtils.extract_energy(text)
        except ImportError:
            # Fallback energy extraction
            import re
            patterns = [
                r'([0-9]+\.[0-9]+)\s*kWh',
                r'(\d+\.\d+)\s*kWh',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        energy = float(match.group(1))
                        if 0 < energy < 200:
                            return energy
                    except:
                        continue
            return None
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from text. Can be overridden by subclasses."""
        try:
            from ..utils import PatternUtils
            return PatternUtils.extract_location(text)
        except ImportError:
            # Fallback location extraction
            import re
            patterns = [
                r'Location[:\s]*([^\n\r]+)',
                r'Station[:\s]*([^\n\r]+)',
                r'Site[:\s]*([^\n\r]+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()[:200]
                    if len(location) > 5:
                        return location
            return None
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration from text. Can be overridden by subclasses."""
        try:
            from ..utils import PatternUtils
            return PatternUtils.extract_duration(text)
        except ImportError:
            # Fallback duration extraction
            import re
            patterns = [
                r'Duration[:\s]*(\d+:\d+(?::\d+)?)',
                r'(\d+)\s*minutes?',
                r'(\d+)m(?:\s*(\d+)s)?',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
            return None
    
    def extract_date(self, text: str) -> datetime:
        """Extract date from text with fallback to current time."""
        try:
            from ..utils import DateUtils
            result = DateUtils.extract_date_from_text(text)
            if result:
                return result
        except ImportError:
            pass
        
        # Fallback date extraction
        import re
        patterns = [
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    if pd:
                        result = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                        if pd.notna(result):
                            return result.to_pydatetime()
                    else:
                        # Try common formats
                        formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%B %d, %Y']
                        for fmt in formats:
                            try:
                                return datetime.strptime(date_str, fmt)
                            except ValueError:
                                continue
                except:
                    continue
        
        # Fallback to current time if no date found
        return datetime.now()