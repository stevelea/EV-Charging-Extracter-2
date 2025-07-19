"""Data models for EV Charging Extractor."""

from .charging_receipt import ChargingReceipt

try:
    from .provider_mapping import ProviderMapping
    __all__ = ['ChargingReceipt', 'ProviderMapping']
except ImportError:
    # Fallback if provider_mapping doesn't exist yet
    __all__ = ['ChargingReceipt']
    
    # Create a simple fallback ProviderMapping class
    class ProviderMapping:
        @classmethod
        def identify_provider(cls, sender: str) -> str:
            """Fallback provider identification."""
            sender_lower = sender.lower()
            if 'chargefox' in sender_lower:
                return 'Chargefox'
            elif 'evie' in sender_lower or 'goevie' in sender_lower:
                return 'EVIE Networks'
            elif 'bppulse' in sender_lower or 'bp' in sender_lower:
                return 'BP Pulse'
            elif 'tesla' in sender_lower:
                return 'Tesla'
            return 'Unknown'
        
        @classmethod
        def is_home_charging(cls, provider: str) -> bool:
            return provider.upper() in ['EVCC (HOME)', 'HOME', 'EVCC']
        
        @classmethod
        def get_search_terms(cls) -> list:
            return [
                '(FROM "DoNotReply@bppulse.com.au")',
                '(FROM "no-reply@goevie.com.au")',
                'FROM "info@chargefox.com"',
                'FROM "noreply@tesla.com" SUBJECT "supercharg"',
            ]
