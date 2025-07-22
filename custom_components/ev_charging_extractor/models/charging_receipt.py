"""ChargingReceipt data model."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib


@dataclass
class ChargingReceipt:
    """Data class for charging receipts."""
    provider: str
    date: datetime
    location: str
    cost: float
    currency: str
    energy_kwh: Optional[float] = None
    session_duration: Optional[str] = None
    email_subject: str = ""
    raw_data: str = ""
    
    def generate_hash(self, source_type: str = 'email') -> str:
        """Generate unique hash for receipt."""
        try:
            hash_components = [
                str(self.provider).lower().strip(),
                str(self.date.strftime('%Y-%m-%d %H:%M')),
                str(self.location).lower().strip(),
                f"{self.cost:.2f}",
                self.currency.upper(),
                source_type
            ]
            
            if self.energy_kwh:
                hash_components.append(f"{self.energy_kwh:.2f}")
            
            hash_string = '|'.join(hash_components)
            return hashlib.sha256(hash_string.encode()).hexdigest()[:16]
        except Exception:
            # Fallback hash
            return hashlib.sha256(str(self.provider + str(self.cost)).encode()).hexdigest()[:16]
    
    def is_valid(self, minimum_cost: float = 0.0) -> bool:
        """Check if receipt has valid data."""
        return (
            bool(self.provider and self.provider != 'Unknown') and
            self.cost > minimum_cost and
            bool(self.location) and
            isinstance(self.date, datetime)
        )
    
    def __str__(self) -> str:
        """String representation of receipt."""
        return f"{self.provider}: ${self.cost:.2f} at {self.location} on {self.date.strftime('%Y-%m-%d')}"
