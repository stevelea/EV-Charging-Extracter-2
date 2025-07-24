"""Provider mapping and identification."""
from typing import Dict, List


class ProviderMapping:
    """Handles provider identification from email senders."""
    
    PROVIDER_MAPPING = {
        'chargefox': 'Chargefox',
        'evie': 'EVIE Networks',
        'goevie': 'EVIE Networks',
        'bppulse': 'BP Pulse',
        'bp': 'BP Pulse',
        'tesla': 'Tesla',
        'chargepoint': 'ChargePoint',
        'nrma': 'NRMA',
        'ampcharge': 'Ampol',
        'ampol': 'Ampol',
        'exploren': 'Exploren',
        'shell': 'Shell Recharge',
        'tritium': 'Tritium',
        'jetcharge': 'JET Charge',
        'schneider': 'Schneider Electric',
        'agl': 'AGL',
        'origin': 'Origin Energy',
        'energex': 'Energex',
        'ausgrid': 'Ausgrid'
    }
    
    @classmethod
    def identify_provider(cls, sender: str) -> str:
        """Identify charging provider from email sender."""
        sender_lower = sender.lower()
        
        # Check direct matches
        for key, provider in cls.PROVIDER_MAPPING.items():
            if key in sender_lower:
                return provider
        
        # Try to extract from email domain
        if '@' in sender:
            try:
                domain_parts = sender.split('@')[1].split('.')
                for part in domain_parts:
                    part_lower = part.lower()
                    for key, provider in cls.PROVIDER_MAPPING.items():
                        if key in part_lower:
                            return provider
                
                # Fallback to domain name
                domain = domain_parts[0] if domain_parts else 'Unknown'
                return domain.title()
            except:
                pass
        
        return 'Unknown'
    
    @classmethod
    def is_home_charging(cls, provider: str) -> bool:
        """Check if provider represents home charging."""
        return provider.upper() in ['EVCC (HOME)', 'HOME', 'EVCC']
    
    @classmethod
    def get_search_terms(cls) -> List[str]:
        """Get email search terms for charging providers."""
        return [
            # BP PULSE - enhanced search patterns
            '(FROM "DoNotReply@bppulse.com.au")',
            '(FROM "noreply@bppulse.com.au")',
            '(FROM "support@bppulse.com.au")',
            '(FROM "bppulse.com.au")',
            '(FROM "bp" SUBJECT "charging")',
            '(FROM "bp" SUBJECT "receipt")',
            '(FROM "bp" SUBJECT "session")',
            
            # EVIE Networks - specific receipt searches
            '(FROM "no-reply@goevie.com.au" SUBJECT "receipt")',
            '(FROM "no-reply@goevie.com.au" SUBJECT "invoice")', 
            '(FROM "no-reply@goevie.com.au" SUBJECT "charging session")',
            '(FROM "no-reply@goevie.com.au" SUBJECT "tax invoice")',
            
            # Chargefox
            'FROM "info@chargefox.com"',
            'FROM "noreply@chargefox.com"',
            
            # Tesla Supercharging
            'FROM "no-reply@tesla.com" SUBJECT "supercharg"',
            'FROM "noreply@tesla.com" SUBJECT "supercharg"',
            
            # ChargePoint
            'FROM "noreply@chargepoint.com"',
            'FROM "support@chargepoint.com"',
            
            # Ampol
            'FROM "ampcharge.com.au"',
            'FROM "noreply@ampol.com.au" SUBJECT "charg"',
            
            # NRMA
            'FROM "noreply@mynrma.com.au" SUBJECT "charg"',
            'FROM "charging@nrma.com.au"',
            
            # Shell Recharge
            'FROM "noreply@shell.com" SUBJECT "charg"',
            'FROM "shellrecharge.com"',
            
            # JET Charge
            'FROM "jetcharge.com.au"',
            
            # Exploren
            'FROM "exploren.com.au"',
            
            # AGL charging
            'FROM "noreply@agl.com.au" SUBJECT "charg"',
            
            # Origin Energy charging
            'FROM "noreply@originenergy.com.au" SUBJECT "charg"'
        ]
