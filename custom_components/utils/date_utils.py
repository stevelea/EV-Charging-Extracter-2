"""Date utilities for parsing and formatting."""
import re
import logging
from datetime import datetime
from typing import Optional

try:
    import pandas as pd
except ImportError:
    pd = None

_LOGGER = logging.getLogger(__name__)


class DateUtils:
    """Utility class for date parsing and formatting."""
    
    @staticmethod
    def extract_date_from_text(text: str) -> Optional[datetime]:
        """Extract date from text using various patterns."""
        if not pd:
            _LOGGER.warning("Pandas not available for date parsing")
            return None
        
        # Import here to avoid circular import
        from .pattern_utils import PatternUtils
        
        date_components = PatternUtils.extract_date_components(text)
        if not date_components:
            return None
        
        date_str, time_str = date_components
        
        try:
            # Handle ISO format dates specifically (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str.strip()):
                # This is ISO format - parse directly without dayfirst
                parsed_date = pd.to_datetime(date_str, format='%Y-%m-%d')
                _LOGGER.debug("Parsed ISO date %s as %s", date_str, parsed_date)
                return parsed_date.to_pydatetime()
            
            # Handle other formats with dayfirst=True for Australian dates
            parsed_date = pd.to_datetime(date_str, dayfirst=True)
            _LOGGER.debug("Parsed date %s as %s", date_str, parsed_date)
            return parsed_date.to_pydatetime()
        except Exception as e:
            _LOGGER.debug("Date parsing failed for '%s': %s", date_str, e)
            return None
    
    @staticmethod
    def parse_date_safely(date_str: str) -> Optional[datetime]:
        """Parse date string with multiple fallback formats."""
        if not date_str or pd is None:
            return None
        
        try:
            # Convert to string if not already
            date_str = str(date_str)
            
            # Handle ISO format dates specifically (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}', date_str):
                # This is ISO format - parse without dayfirst to avoid confusion
                result = pd.to_datetime(date_str, errors='coerce')
                if pd.notna(result):
                    _LOGGER.debug("Parsed ISO date %s as %s", date_str, result)
                    return result.to_pydatetime()
            
            # Handle DD/MM/YYYY or DD-MM-YYYY formats
            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_str):
                # This looks like DD/MM/YYYY - use dayfirst=True
                result = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                if pd.notna(result):
                    _LOGGER.debug("Parsed DD/MM date %s as %s", date_str, result)
                    return result.to_pydatetime()
            
            # Try pandas auto-parsing for other formats
            result = pd.to_datetime(date_str, errors='coerce')
            if pd.notna(result):
                return result.to_pydatetime()
            
        except Exception as e:
            _LOGGER.debug("Exception parsing date %s: %s", date_str, e)
        
        try:
            # Try manual ISO parsing with timezone handling
            if 'T' in date_str and '+' in date_str:
                # Split at timezone
                dt_part, tz_part = date_str.split('+')
                # Remove excessive microseconds (keep only 6 digits)
                if '.' in dt_part:
                    base_dt, microsecs = dt_part.split('.')
                    microsecs = microsecs[:6].ljust(6, '0')  # Truncate or pad to 6 digits
                    dt_part = f"{base_dt}.{microsecs}"
                
                # Reconstruct with timezone
                cleaned_date = f"{dt_part}+{tz_part}"
                result = pd.to_datetime(cleaned_date, errors='coerce')
                if pd.notna(result):
                    return result.to_pydatetime()
        except Exception as e:
            _LOGGER.debug("Manual timezone parsing failed for %s: %s", date_str, e)
        
        _LOGGER.warning("Could not parse date: %s", date_str)
        return None
    
    @staticmethod
    def format_date_for_display(date_obj: datetime) -> str:
        """Format datetime object for user-friendly display."""
        try:
            if isinstance(date_obj, str):
                date_obj = DateUtils.parse_date_safely(date_obj)
            
            if isinstance(date_obj, datetime):
                # Format as DD-MM-YY HH:MM (Australian format)
                return date_obj.strftime('%d-%m-%y %H:%M')
            else:
                return 'Unknown'
        except Exception as e:
            _LOGGER.debug("Error formatting date: %s", e)
            return str(date_obj) if date_obj else 'Unknown'
    
    @staticmethod
    def is_recent_date(date_obj: datetime, days_back: int = 30) -> bool:
        """Check if date is within the specified number of days back."""
        try:
            if not isinstance(date_obj, datetime):
                date_obj = DateUtils.parse_date_safely(str(date_obj))
            
            if not date_obj:
                return False
            
            if pd:
                cutoff_date = datetime.now() - pd.Timedelta(days=days_back)
            else:
                from datetime import timedelta
                cutoff_date = datetime.now() - timedelta(days=days_back)
            
            return date_obj >= cutoff_date
        except Exception:
            return False
