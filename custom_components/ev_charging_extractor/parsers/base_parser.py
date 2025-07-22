"""Base parser class for EV charging providers."""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional

try:
    import pandas as pd
except ImportError:
    pd = None

from ..models import ChargingReceipt
from ..utils import PatternUtils, DateUtils

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
        return PatternUtils.extract_cost(text)
    
    def extract_energy(self, text: str) -> Optional[float]:
        """Extract energy from text. Can be overridden by subclasses."""
        return PatternUtils.extract_energy(text)
    
    def extract_location(self, text: str) -> Optional[str]:
        """Extract location from text. Can be overridden by subclasses."""
        return PatternUtils.extract_location(text)
    
    def extract_duration(self, text: str) -> Optional[str]:
        """Extract duration from text. Can be overridden by subclasses."""
        return PatternUtils.extract_duration(text)
    
    def extract_date(self, text: str) -> datetime:
        """Extract date from text with fallback to current time."""
        if not DateUtils:
            return datetime.now()
        
        return DateUtils.extract_date_from_text(text) or datetime.now()
