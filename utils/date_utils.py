"""Date utilities for parsing and formatting - compatible version."""
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
        if not text:
            return None
        
        # Enhanced date patterns with priority order
        date_patterns = [
            # ISO format (YYYY-MM-DD) - highest priority
            (r'(\d{4}-\d{1,2}-\d{1,2})', '%Y-%m-%d', False),
            
            # Australian format (DD/MM/YYYY)
            (r'(\d{1,2}/\d{1,2}/\d{4})', '%d/%m/%Y', True),
            
            # US format (MM/DD/YYYY) 
            (r'(\d{1,2}/\d{1,2}/\d{4})', '%m/%d/%Y', False),
            
            # Tesla format (YYYY/MM/DD)
            (r'(\d{4}/\d{1,2}/\d{1,2})', '%Y/%m/%d', False),
            
            # Date with time - extract date part
            (r'(\d{1,2}/\d{1,2}/\d{4})\s+\d{1,2}:\d{2}', '%d/%m/%Y', True),
            (r'(\d{4}-\d{1,2}-\d{1,2})\s+\d{1,2}:\d{2}', '%Y-%m-%d', False),
            
            # Month name formats
            (r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})', '%d %B %Y', False),
            (r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})', '%B %d, %Y', False),
            
            # Alternative separators
            (r'(\d{1,2}-\d{1,2}-\d{4})', '%d-%m-%Y', True),
            (r'(\d{4}\.\d{1,2}\.\d{1,2})', '%Y.%m.%d', False),
            (r'(\d{1,2}\.\d{1,2}\.\d{4})', '%d.%m.%Y', True),
        ]
        
        for pattern, date_format, is_day_first in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).strip()
                    
                    # Try pandas first if available and format needs it
                    if pd and ('/' in date_str or '-' in date_str) and len(date_str.split('/')) == 3:
                        try:
                            # Use pandas with dayfirst parameter
                            if is_day_first:
                                parsed_date = pd.to_datetime(date_str, dayfirst=True, errors='raise')
                            else:
                                parsed_date = pd.to_datetime(date_str, errors='raise')
                            
                            result = parsed_date.to_pydatetime()
                            _LOGGER.debug("Parsed date with pandas: %s -> %s (dayfirst=%s)", 
                                        date_str, result, is_day_first)
                            return result
                        except:
                            pass  # Fall through to manual parsing
                    
                    # Manual parsing with specific format
                    try:
                        result = datetime.strptime(date_str, date_format)
                        _LOGGER.debug("Parsed date manually: %s -> %s (format: %s)", 
                                    date_str, result, date_format)
                        return result
                    except ValueError:
                        # Try alternative formats for the same pattern
                        if date_format == '%d/%m/%Y':
                            try:
                                result = datetime.strptime(date_str, '%m/%d/%Y')
                                _LOGGER.debug("Parsed date with US format fallback: %s -> %s", date_str, result)
                                return result
                            except ValueError:
                                pass
                        elif date_format == '%m/%d/%Y':
                            try:
                                result = datetime.strptime(date_str, '%d/%m/%Y')
                                _LOGGER.debug("Parsed date with AU format fallback: %s -> %s", date_str, result)
                                return result
                            except ValueError:
                                pass
                        continue
                        
                except Exception as e:
                    _LOGGER.debug("Date parsing failed for '%s' with pattern '%s': %s", 
                                date_str, pattern, e)
                    continue
        
        _LOGGER.warning("Could not parse any date from text: %s", text[:100])
        return None
    
    @staticmethod
    def extract_date_components(text: str) -> Optional[tuple]:
        """Extract date and time components from text."""
        # Enhanced patterns for different providers
        datetime_patterns = [
            # Tesla patterns
            r'Invoice\s+date\s+(\d{4}/\d{2}/\d{2})',
            r'Date\s+of\s+Event[^\n]*(\d{4}/\d{2}/\d{2})',
            
            # BP Pulse patterns
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
            
            # EVIE patterns  
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*[A-Z]{3,4})',
            
            # Chargefox patterns
            r'EV\s+charging\s+at[^\n]*on\s+(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+at\s+(\d{1,2}:\d{2})',
            
            # Ampol patterns
            r'Start\s+Time[:\s]*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}\s*[AP]M)',
            
            # General patterns
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
        ]
        
        for pattern in datetime_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    return match.group(1), match.group(2)
                else:
                    return match.group(1), None
        
        return None
    
    @staticmethod
    def parse_date_safely(date_str: str) -> Optional[datetime]:
        """Parse date string with multiple fallback formats and validation."""
        if not date_str:
            return None
        
        try:
            # First try the enhanced extraction
            result = DateUtils.extract_date_from_text(str(date_str))
            if result:
                # Validate the result is reasonable (not too far in future/past)
                now = datetime.now()
                if result.year < 2020 or result.year > now.year + 1:
                    _LOGGER.warning("Parsed date seems unreasonable: %s from '%s'", result, date_str)
                    return None
                return result
            
            # If that fails, try pandas with different settings
            if pd:
                try:
                    # Try with dayfirst=True (Australian format)
                    result = pd.to_datetime(date_str, dayfirst=True, errors='raise')
                    if pd.notna(result):
                        return result.to_pydatetime()
                except:
                    try:
                        # Try with dayfirst=False (US format)
                        result = pd.to_datetime(date_str, dayfirst=False, errors='raise')
                        if pd.notna(result):
                            return result.to_pydatetime()
                    except:
                        pass
            
            return None
            
        except Exception as e:
            _LOGGER.debug("Date parsing completely failed for '%s': %s", date_str, e)
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
            
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days_back)
            return date_obj >= cutoff_date
        except Exception:
            return False


# Alias for backward compatibility
EnhancedDateUtils = DateUtils