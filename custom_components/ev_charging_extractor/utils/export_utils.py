"""Export utilities for EV charging data."""
import os
import re
import logging
from typing import List, Dict, Any

try:
    import pandas as pd
except ImportError:
    pd = None

from .date_utils import DateUtils

_LOGGER = logging.getLogger(__name__)


class ExportUtils:
    """Utility class for data export operations."""
    
    def __init__(self, csv_path: str, database_manager):
        """Initialize export utilities."""
        self.csv_path = csv_path
        self.database_manager = database_manager
    
    def export_to_csv(self):
        """Export charging data to CSV with robust date parsing."""
        try:
            if not pd:
                _LOGGER.error("Pandas not available for CSV export")
                return
            
            # Get all receipts from database
            receipts = self.database_manager.get_all_receipts()
            
            if not receipts:
                _LOGGER.warning("No data to export")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(receipts)
            
            # Robust date parsing for different formats
            def parse_date_with_format_detection(date_str):
                """Parse date string with format detection."""
                if pd.isna(date_str) or date_str is None:
                    return None
                
                try:
                    # Convert to string if not already
                    date_str = str(date_str)
                    
                    # Handle ISO format dates specifically (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                    if re.match(r'^\d{4}-\d{1,2}-\d{1,2}', date_str):
                        # This is ISO format - parse without dayfirst to avoid confusion
                        result = pd.to_datetime(date_str, errors='coerce')
                        if pd.notna(result):
                            return result
                    
                    # Handle DD/MM/YYYY or DD-MM-YYYY formats
                    if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_str):
                        # This looks like DD/MM/YYYY - use dayfirst=True
                        result = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                        if pd.notna(result):
                            return result
                    
                    # Try auto-parsing for other formats
                    return pd.to_datetime(date_str, errors='coerce')
                    
                except Exception:
                    return pd.NaT
            
            # Apply smart date parsing
            df['date'] = df['date'].apply(parse_date_with_format_detection)
            df['created_at'] = df['created_at'].apply(parse_date_with_format_detection)
            
            # Drop rows where date parsing failed
            df = df.dropna(subset=['date'])
            
            if df.empty:
                _LOGGER.warning("No valid dates found after parsing")
                return
            
            # Format dates as dd-mm-yy hh:mm in local time
            df['date_formatted'] = df['date'].apply(DateUtils.format_date_for_display)
            df['created_at_formatted'] = df['created_at'].apply(DateUtils.format_date_for_display)
            
            # Reorder columns and rename for user-friendliness
            export_df = df[[
                'date_formatted',
                'provider', 
                'location',
                'energy_kwh',
                'session_duration',
                'cost',
                'currency',
                'source_type',
                'created_at_formatted'
            ]].copy()
            
            # Rename columns to be more user-friendly
            export_df.columns = [
                'Session Date & Time',
                'Provider',
                'Location', 
                'Energy (kWh)',
                'Duration',
                'Cost',
                'Currency',
                'Source',
                'Added to Database'
            ]
            
            # Round energy to 2 decimal places for cleaner display
            export_df['Energy (kWh)'] = pd.to_numeric(export_df['Energy (kWh)'], errors='coerce').round(2)
            
            # Round cost to 2 decimal places
            export_df['Cost'] = pd.to_numeric(export_df['Cost'], errors='coerce').round(2)
            
            # Save to CSV
            export_df.to_csv(self.csv_path, index=False)
            _LOGGER.info("✅ Exported %d receipts to %s with user-friendly formatting", len(export_df), self.csv_path)
            
        except Exception as e:
            _LOGGER.error("Error exporting to CSV: %s", e)
    
    def clear_csv_file(self):
        """Clear the CSV export file."""
        try:
            if os.path.exists(self.csv_path):
                os.remove(self.csv_path)
                _LOGGER.info("Cleared CSV file: %s", self.csv_path)
        except Exception as e:
            _LOGGER.error("Error clearing CSV file: %s", e)
    
    def get_csv_stats(self) -> Dict[str, Any]:
        """Get statistics about the CSV export."""
        try:
            if not os.path.exists(self.csv_path):
                return {'exists': False, 'size': 0, 'rows': 0}
            
            file_size = os.path.getsize(self.csv_path)
            
            # Count rows if pandas is available
            row_count = 0
            if pd:
                try:
                    df = pd.read_csv(self.csv_path)
                    row_count = len(df)
                except:
                    pass
            
            return {
                'exists': True,
                'size': file_size,
                'rows': row_count,
                'path': self.csv_path
            }
            
        except Exception as e:
            _LOGGER.error("Error getting CSV stats: %s", e)
            return {'exists': False, 'size': 0, 'rows': 0, 'error': str(e)}
