"""Pattern utilities for data extraction."""
import re
from typing import List, Optional, Tuple


class PatternUtils:
    """Utility class for pattern matching and data extraction."""
    
    # Cost extraction patterns - BP PULSE specific patterns FIRST
    COST_PATTERNS = [
        # BP PULSE SPECIFIC PATTERNS (check these FIRST)
        r'\*\*Total\s+Cost\*\*[^\d]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # **Total Cost** **14.95 AUD**
        r'\*\*Total\s+Sales\s+Amount\*\*[^\d]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # **Total Sales Amount** **14.95 AUD**
        r'Total\s+Cost[:\s]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # Total Cost **14.95 AUD**
        r'Total\s+Sales\s+Amount[:\s]*\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # Total Sales Amount **14.95 AUD**
        r'Sale\s+Amount[:\s]*([0-9]+\.[0-9]{2})\s+AUD',  # Sale Amount 14.95 AUD
        r'Energy\s+Cost[:\s]*([0-9]+\.[0-9]{2})\s+AUD',  # Energy Cost 14.95 AUD
        
        # EVIE SPECIFIC PATTERNS
        r'\*\*([0-9]+\.[0-9]{2})\s+AUD\*\*',  # **19.54 AUD** (catch-all for EVIE)
        r'Total\s+Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount: $19.54
        r'Amount\s+Due[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount Due: $19.54
        
        # AMPOL specific patterns
        r'\*\*\$([0-9]+\.[0-9]{2})\*\*\s+for\s+EV\s+charging',  # **$44.53** for EV charging
        r'Total\s+Cost[:\s]*\*\*\$([0-9]+\.[0-9]{2})\*\*',  # **Total Cost** **$44.53**
        
        # CHARGEFOX SPECIFIC
        r'Total\s+Amount\s+including\s+GST[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount including GST $10.46
        r'Payments[:\s]*Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Payments Amount $10.46
        r'Total\s+Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Total Amount $10.46
        r'Amount\s+Charged[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount Charged $10.46
        r'Session\s+Cost[:\s]*\$([0-9]+\.[0-9]{2})',  # Session Cost $10.46
        r'Charging\s+Cost[:\s]*\$([0-9]+\.[0-9]{2})',  # Charging Cost $10.46
        r'You\s+paid[:\s]*\$([0-9]+\.[0-9]{2})',  # You paid $10.46
        r'Payment[:\s]*\$([0-9]+\.[0-9]{2})',  # Payment $10.46
        r'GST\s+Inclusive[:\s]*\$([0-9]+\.[0-9]{2})',  # GST Inclusive: $10.46
        r'EV\s+charging[:\s]*\$([0-9]+\.[0-9]{2})',  # EV charging: $10.46
        r'Charging\s+fee[:\s]*\$([0-9]+\.[0-9]{2})',  # Charging fee: $10.46
        
        # Tesla Supercharging patterns
        r'Supercharging[:\s]*\$([0-9]+\.[0-9]{2})',  # Supercharging: $12.34
        r'Tesla\s+Supercharging[:\s]*\$([0-9]+\.[0-9]{2})',  # Tesla Supercharging: $12.34
        
        # General invoice patterns
        r'Total[:\s]*\$([0-9]+\.[0-9]{2})',  # Total: $12.34
        r'Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Amount: $12.34
        r'Final\s+Amount[:\s]*\$([0-9]+\.[0-9]{2})',  # Final Amount: $12.34
        r'Invoice\s+Total[:\s]*\$([0-9]+\.[0-9]{2})',  # Invoice Total: $12.34
        r'TOTAL[:\s]*\$([0-9]+\.[0-9]{2})',  # TOTAL: $12.34
        
        # General Australian dollar patterns
        r'([0-9]+\.[0-9]{2})\s*AUD',  # 12.34 AUD
        r'AUD\s*([0-9]+\.[0-9]{2})',  # AUD 12.34
        r'Total\s*\$([0-9]+\.[0-9]{2})\s+AUD',  # Total $10.46 AUD
        r'\$([0-9]+\.[0-9]{2})',  # $12.34 (fallback)
    ]
    
    # Enhanced date extraction with BP PULSE specific patterns
    DATE_PATTERNS = [
        # BP PULSE specific patterns (check these FIRST)
        r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*[A-Z]{3,4})',  # March 25, 2025 at 7:05:04 PM AEDT
        r'Start\s+Time[:\s]*([A-Za-z]{3}\s+\d{1,2},\s+\d{4}),\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',  # Start Time Mar 25, 2025, 6:30:49 PM
        r'End\s+Time[:\s]*([A-Za-z]{3}\s+\d{1,2},\s+\d{4}),\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',  # End Time Mar 25, 2025, 7:05:04 PM
        
        # EVIE specific patterns
        r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*[A-Z]{3,4})',  # July 4, 2025 at 7:54:13 PM AEST
        
        # Ampol specific patterns
        r'Start\s+Time[:\s]*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}\s*[AP]M)',  # Start Time 04/06/2025 01:29 PM
        r'End\s+Time[:\s]*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}\s*[AP]M)',  # End Time 04/06/2025 02:10 PM
        r'(\d{2}/\d{2}/\d{4})',  # 04/06/2025
        
        # Chargefox specific patterns
        r'EV\s+charging\s+at[^\n]*on\s+(\d{4}-\d{2}-\d{2})',  # EV charging at ... on 2025-04-11 (ISO format)
        r'Date[:\s]*(\d{1,2}\s+[A-Za-z]{3,9},\s+\d{4})',  # Date: 7 July, 2025
        r'Session\s+date[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # Session date: 07/07/2025
        r'Charged\s+on[:\s]*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # Charged on: July 7, 2025
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+at\s+\d{1,2}:\d{2}',  # 07/07/2025 at 14:30
        
        # Standard patterns
        r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',  # July 2, 2025
        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4})',  # DD Month YYYY
    ]
    
    # Enhanced location extraction with BP PULSE specific patterns
    LOCATION_PATTERNS = [
        # BP PULSE specific patterns (check these FIRST)
        r'Location\s+bp\s+pulse\s+([A-Za-z\s]+)\s+([^\n\r]+Drive[^\n\r,]*,\s*[A-Za-z\s]+,?\s*\d{4})',  # Location bp pulse Beresfield John Renshaw Drive...
        r'bp\s+pulse\s+([A-Za-z\s]+)[^\n\r]*([A-Za-z\s]+Drive[^\n\r,]*,\s*[A-Za-z\s]+,?\s*\d{4})',  # bp pulse Beresfield ... Drive Beresfield, New South Wales 2322
        r'Location[:\s]*([^\n\r]+bp\s+pulse[^\n\r]+)',  # Location with bp pulse
        
        # EVIE specific patterns
        r'Location[:\s]*([^\n\r]+Service Centre[^\n\r]*\d+[^\n\r]*,\s*[A-Z]{2,3}\s*\d{4})',  # Location Taree South Service Centre 201 Manning River Drive Glenthorne, NSW 2430
        r'([A-Za-z\s]+Service Centre)[^\n\r]*(\d+\s+[A-Za-z\s]+(?:Drive|Road|Street|Ave|Avenue)[^\n\r,]*,\s*[A-Z]{2,3}\s*\d{4})',  # Service Centre + Address
        r'Station\s+ID[:\s]*[A-Z0-9]+[^\n]*Location[:\s]*([^\n\r]+)',  # After Station ID, find Location
        r'([A-Za-z\s]+-[A-Za-z\s]+)[^\n\r]*(\d+-?\d*\s+[A-Za-z\s]+(?:Highway|Hwy|Street|St|Road|Rd|Avenue|Ave|Drive|Dr)[^\n\r,]*,\s*[A-Z]{2,3}\s*\d{4})',  # Name + Address
        
        # Ampol specific patterns
        r'(Pacific Highway \d+-\d+, [A-Za-z\s]+ \d{4})',  # Pacific Highway 59-61, Waitara 2077
        r'(Ampol Foodary [A-Za-z\s]+)',  # Ampol Foodary Waitara
        
        # Chargefox specific patterns
        r'EV\s+charging\s+at\s+([^,\n\r]+,\s*[A-Z]{2,3},?\s*\d{4})\s+on',  # EV charging at location, STATE, 1234 on
        r'charging\s+at\s+([^\n\r]+)\s+on\s+\d{4}',  # charging at location on date
        r'([A-Za-z\s]+(?:Shopping Centre|Center|Mall|Plaza))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Shopping centers
        r'([A-Za-z\s]+(?:Service Centre|Station))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Service stations
        r'([A-Za-z\s]+(?:Hotel|Motel))[^\n\r]*([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Hotels
        
        # Standard location patterns
        r'Location[:\s]*([^\n\r]+)',  # Location: ...
        r'Site[:\s]*([^\n\r]+)',  # Site: ...
        r'Station[:\s]*([^\n\r]+)',  # Station: ...
        r'Address[:\s]*([^\n\r]+)',  # Address: ...
        r'Charging\s+station[:\s]*([^\n\r]+)',  # Charging station: ...
        r'Venue[:\s]*([^\n\r]+)',  # Venue: ...
        
        # Try to find full addresses
        r'(\d+-\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^\n\r,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Full address with range
        r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^\n\r,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Full address
        r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^\n\r,]*,\s*[A-Z]{2,3}\s*\d{4})',  # Address without suburb
        
        # Try to find suburb, state patterns
        r'([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Suburb, STATE 1234
    ]
    
    # Enhanced energy extraction with BP PULSE specific patterns
    ENERGY_PATTERNS = [
        # BP PULSE specific patterns (check these FIRST)
        r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total Energy 27.1750 kWh
        r'Energy\s+Distributed[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Distributed 27.1750 kWh
        
        # EVIE specific patterns
        r'Total\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total Energy 26.4047 kWh
        r'Energy\s+Consumed[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Consumed 26.4047 kWh
        r'kWh\s+Delivered[:\s]*([0-9]+\.[0-9]+)',  # kWh Delivered 26.4047
        
        # Ampol specific patterns
        r'Energy\s+Delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Delivered 64.532 kWh
        
        # Chargefox specific patterns
        r'Charging\s+for\s+\d+mins?,\s+([0-9]+\.[0-9]+)kWh',  # Charging for 8mins, 16.37kWh
        r'([0-9]+\.[0-9]+)kWh\s+@\s+\$[0-9]+\.[0-9]+/kWh',  # 16.37kWh @ $0.71/kWh
        r'Energy\s+delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy delivered: 16.37 kWh
        r'Total\s+energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Total energy: 16.37 kWh
        r'kWh\s+consumed[:\s]*([0-9]+\.[0-9]+)',  # kWh consumed: 16.37
        r'([0-9]+\.[0-9]+)\s*kWh\s+delivered',  # 16.37 kWh delivered
        r'([0-9]+\.[0-9]+)\s*kWh\s+charged',  # 16.37 kWh charged
        r'Charged[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Charged: 16.37 kWh
        r'Session\s+energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Session energy: 16.37 kWh
        r'Power\s+delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Power delivered: 16.37 kWh
        
        # Standard patterns
        r'(\d+\.\d+)\s*kWh',  # 12.34 kWh (more specific first)
        r'(\d+)\.\d*\s*kWh',  # 12.xx kWh
        r'(\d+)\s*kWh',  # 12 kWh
        r'(\d+\.?\d*)\s*KWH',  # 12.34 KWH (uppercase)
        r'Energy[:\s]*(\d+\.?\d*)',  # Energy: 12.34
        r'kWh[:\s]*([0-9]+\.[0-9]+)',  # kWh: 16.37
        r'([0-9]+\.[0-9]+)\s+kilowatt.hours?',  # 16.37 kilowatt hours
    ]
    
    # Duration extraction with BP PULSE specific patterns
    DURATION_PATTERNS = [
        # BP PULSE specific patterns (check these FIRST)
        r'Charging\s+Time[:\s]*(\d+)m',  # Charging Time 34m
        r'(\d+)m(?:\s*(\d+)s)?',  # 34m or 34m 30s
        
        # EVIE specific patterns
        r'Charging\s+Time[:\s]*(\d+)m',  # Charging Time 13m
        r'Session\s+Duration[:\s]*(\d+:\d+)',  # Session Duration: 00:13
        r'Duration[:\s]*(\d+\s+minutes?)',  # Duration: 13 minutes
        
        # Ampol specific patterns
        r'Duration[:\s]*(\d{2}:\d{2}:\d{2})',  # Duration 00:40:11
        
        # Chargefox specific patterns
        r'Charging\s+for\s+(\d+mins?)',  # Charging for 8mins
        r'Session\s+duration[:\s]*(\d+:\d+(?::\d+)?)',  # Session duration: 00:08:30
        r'Duration[:\s]*(\d+:\d+(?::\d+)?)',  # Duration: 00:08:30
        r'Time[:\s]*(\d+:\d+(?::\d+)?)',  # Time: 00:08:30
        r'(\d+)\s*minutes?\s+charging',  # 8 minutes charging
        r'(\d+)\s*mins?\s+session',  # 8 mins session
        r'Charged\s+for[:\s]*(\d+)\s*minutes?',  # Charged for: 8 minutes
        r'Session\s+time[:\s]*(\d+)\s*minutes?',  # Session time: 8 minutes
        r'(\d+)\s*hours?\s*(\d+)?\s*minutes?',  # 1 hour 30 minutes
        r'(\d+)h\s*(\d+)?m',  # 1h 30m
        
        # Standard patterns
        r'Duration[:\s]*([^\n\r]+)',  # Duration: ...
        r'Time[:\s]*(\d+:\d+)',  # Time: HH:MM
        r'(\d+)\s*minutes?',  # X minutes
        r'(\d+)\s*hours?\s*(\d+)?\s*minutes?',  # X hours Y minutes
        
        # Time range patterns
        r'from\s+\d{1,2}:\d{2}\s+to\s+\d{1,2}:\d{2}',  # from 14:30 to 14:38
        r'Start[:\s]*\d{1,2}:\d{2}[^\n]*End[:\s]*\d{1,2}:\d{2}',  # Start: 14:30 ... End: 14:38
    ]
    
    @classmethod
    def extract_cost(cls, text: str) -> Optional[float]:
        """Extract cost from text using patterns."""
        for pattern in cls.COST_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    if cost_value > 0:
                        return cost_value
                except (ValueError, IndexError):
                    continue
        return None
    
    @classmethod
    def extract_energy(cls, text: str) -> Optional[float]:
        """Extract energy from text using patterns."""
        for pattern in cls.ENERGY_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        return energy_value
                except (ValueError, IndexError):
                    continue
        return None
    
    @classmethod
    def extract_location(cls, text: str) -> Optional[str]:
        """Extract location from text using patterns."""
        for pattern in cls.LOCATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    # For patterns with multiple groups, combine them
                    location = f"{match.group(1).strip()} {match.group(2).strip()}"
                else:
                    location = match.group(1).strip()
                
                # Clean up the location
                location = location.replace('\n', ' ').replace('\r', ' ')
                location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
                location = location[:200]  # Limit length
                
                if location and len(location) > 5:  # Ensure meaningful location
                    return location
        return None
    
    @classmethod
    def extract_duration(cls, text: str) -> Optional[str]:
        """Extract session duration from text using patterns."""
        for pattern in cls.DURATION_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1 and match.group(2):
                    # Handle patterns with hours and minutes
                    hours = match.group(1)
                    minutes = match.group(2)
                    return f"{hours}h {minutes}m"
                else:
                    return match.group(1).strip()
        return None
    
    @classmethod
    def extract_date_components(cls, text: str) -> Optional[Tuple[str, Optional[str]]]:
        """Extract date and time components from text."""
        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    # Handle patterns with time
                    date_str = f"{match.group(1)} {match.group(2)}"
                    return date_str, match.group(2)
                else:
                    date_str = match.group(1).strip()
                    # Clean up common date string issues
                    date_str = re.sub(r'[,.]$', '', date_str)
                    return date_str, None
        return None
