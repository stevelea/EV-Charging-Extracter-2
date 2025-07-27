"""Utility functions for EV Charging Extractor."""

from .email_utils import EmailUtils
from .pattern_utils import PatternUtils
from .export_utils import ExportUtils

# Try to import date utils - handle both old and new class names
try:
    from .date_utils import DateUtils
except ImportError:
    try:
        from .date_utils import EnhancedDateUtils as DateUtils
    except ImportError:
        # Create a minimal DateUtils class if neither exists
        class DateUtils:
            @staticmethod
            def extract_date_from_text(text):
                from datetime import datetime
                return datetime.now()
            
            @staticmethod
            def parse_date_safely(date_str):
                from datetime import datetime
                try:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except:
                    return None
            
            @staticmethod
            def format_date_for_display(date_obj):
                if hasattr(date_obj, 'strftime'):
                    return date_obj.strftime('%d-%m-%y %H:%M')
                return str(date_obj)

__all__ = ['EmailUtils', 'PatternUtils', 'ExportUtils', 'DateUtils']