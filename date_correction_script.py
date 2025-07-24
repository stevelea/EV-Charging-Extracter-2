"""Script to correct incorrect dates in existing charging receipts."""
import sqlite3
import logging
import re
from datetime import datetime
from typing import Optional, List, Tuple

_LOGGER = logging.getLogger(__name__)


class DateCorrector:
    """Utility to correct incorrect dates in charging receipts."""
    
    def __init__(self, db_path: str):
        """Initialize the date corrector."""
        self.db_path = db_path
    
    def analyze_date_issues(self) -> List[Tuple[int, str, str, str]]:
        """Analyze receipts with potentially incorrect dates."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all receipts ordered by date
            cursor.execute('''
                SELECT id, provider, date, email_subject, raw_data, created_at
                FROM charging_receipts
                ORDER BY date DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            issues = []
            today = datetime.now().date()
            
            for row in rows:
                receipt_id, provider, date_str, subject, raw_data, created_at = row
                
                try:
                    receipt_date = datetime.fromisoformat(date_str).date()
                    created_date = datetime.fromisoformat(created_at).date()
                    
                    # Flag receipts where the receipt date is the same as created date
                    # and the created date is recent (likely today's date was used as fallback)
                    if (receipt_date == created_date and 
                        receipt_date == today and 
                        raw_data):  # Only if we have raw data to re-extract from
                        
                        issues.append((receipt_id, provider, date_str, subject))
                        
                except Exception as e:
                    _LOGGER.debug("Error analyzing receipt %d: %s", receipt_id, e)
            
            return issues
            
        except Exception as e:
            _LOGGER.error("Error analyzing date issues: %s", e)
            return []
    
    def extract_date_from_raw_data(self, raw_data: str, provider: str) -> Optional[datetime]:
        """Enhanced date extraction from raw receipt data."""
        if not raw_data:
            return None
        
        # Provider-specific date patterns
        patterns_by_provider = {
            'Tesla': [
                r'Invoice\s+date\s+(\d{4}/\d{2}/\d{2})',
                r'Date\s+of\s+Event[^\n]*(\d{4}/\d{2}/\d{2})',
                r'(\d{4}/\d{2}/\d{2})',
            ],
            'BP Pulse': [
                r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M)',
                r'Start\s+Time[:\s]*([A-Za-z]{3}\s+\d{1,2},\s+\d{4})',
                r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            ],
            'EVIE Networks': [
                r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s+at\s+(\d{1,2}:\d{2}:\d{2}\s*[AP]M\s*[A-Z]{3,4})',
                r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            ],
            'Chargefox': [
                r'EV\s+charging\s+at[^\n]*on\s+(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{1,2}-\d{1,2})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
            ],
            'Ampol': [
                r'Start\s+Time[:\s]*(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}\s*[AP]M)',
                r'(\d{2}/\d{2}/\d{4})',
            ]
        }
        
        # Get patterns for this provider, or use general patterns
        patterns = patterns_by_provider.get(provider, [])
        
        # Add general patterns as fallback
        general_patterns = [
            r'\b(\d{4}-\d{1,2}-\d{1,2})\b',
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',
            r'\b(\d{2}/\d{2}/\d{4})\b',
            r'\b([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b',
        ]
        
        all_patterns = patterns + general_patterns
        
        for pattern in all_patterns:
            match = re.search(pattern, raw_data, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1).strip()
                    
                    # Try different parsing approaches
                    parsed_date = self._parse_date_string(date_str, provider)
                    if parsed_date:
                        # Validate the date is reasonable
                        now = datetime.now()
                        if 2020 <= parsed_date.year <= now.year + 1:
                            return parsed_date
                        
                except Exception as e:
                    _LOGGER.debug("Failed to parse date '%s' for %s: %s", date_str, provider, e)
                    continue
        
        return None
    
    def _parse_date_string(self, date_str: str, provider: str) -> Optional[datetime]:
        """Parse a date string using multiple formats."""
        # Common date formats to try
        formats = [
            '%Y/%m/%d',      # Tesla: 2025/02/09
            '%Y-%m-%d',      # Chargefox: 2025-02-09
            '%d/%m/%Y',      # Australian: 09/02/2025
            '%m/%d/%Y',      # US: 02/09/2025
            '%B %d, %Y',     # March 25, 2025
            '%b %d, %Y',     # Mar 25, 2025
            '%d %B %Y',      # 25 March 2025
            '%d %b %Y',      # 25 Mar 2025
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try pandas if available
        try:
            import pandas as pd
            
            # For Australian providers, try dayfirst=True
            if provider in ['BP Pulse', 'EVIE Networks', 'Ampol', 'Chargefox']:
                result = pd.to_datetime(date_str, dayfirst=True, errors='raise')
            else:
                result = pd.to_datetime(date_str, errors='raise')
            
            if pd.notna(result):
                return result.to_pydatetime()
                
        except:
            pass
        
        return None
    
    def fix_receipt_dates(self, receipt_ids: List[int] = None) -> dict:
        """Fix dates for specified receipts or all problematic ones."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get receipts to fix
            if receipt_ids:
                placeholders = ','.join(['?'] * len(receipt_ids))
                cursor.execute(f'''
                    SELECT id, provider, date, raw_data, email_subject
                    FROM charging_receipts
                    WHERE id IN ({placeholders})
                ''', receipt_ids)
            else:
                # Find all receipts with today's date (likely incorrect)
                today_str = datetime.now().date().isoformat()
                cursor.execute('''
                    SELECT id, provider, date, raw_data, email_subject
                    FROM charging_receipts
                    WHERE date LIKE ? AND raw_data IS NOT NULL AND raw_data != ''
                ''', (f'{today_str}%',))
            
            receipts_to_fix = cursor.fetchall()
            
            fixed_count = 0
            failed_count = 0
            
            for receipt in receipts_to_fix:
                receipt_id, provider, old_date, raw_data, subject = receipt
                
                # Try to extract correct date
                correct_date = self.extract_date_from_raw_data(raw_data, provider)
                
                if correct_date:
                    # Update the receipt with correct date
                    cursor.execute('''
                        UPDATE charging_receipts
                        SET date = ?
                        WHERE id = ?
                    ''', (correct_date.isoformat(), receipt_id))
                    
                    fixed_count += 1
                    _LOGGER.info("Fixed receipt %d (%s): %s -> %s", 
                               receipt_id, provider, old_date, correct_date.isoformat())
                else:
                    failed_count += 1
                    _LOGGER.warning("Could not extract correct date for receipt %d (%s)", 
                                  receipt_id, provider)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'fixed_count': fixed_count,
                'failed_count': failed_count,
                'total_processed': len(receipts_to_fix)
            }
            
        except Exception as e:
            _LOGGER.error("Error fixing receipt dates: %s", e)
            return {
                'success': False,
                'error': str(e),
                'fixed_count': 0,
                'failed_count': 0
            }
    
    def create_date_fix_service(self, hass, processor):
        """Create a Home Assistant service to fix dates."""
        
        async def fix_receipt_dates_service(call):
            """Service to fix incorrect receipt dates."""
            try:
                _LOGGER.info("Date correction service triggered")
                
                # Run the date correction
                result = await hass.async_add_executor_job(self.fix_receipt_dates)
                
                if result['success']:
                    message = (f"Date correction complete: "
                              f"{result['fixed_count']} receipts fixed, "
                              f"{result['failed_count']} failed")
                else:
                    message = f"Date correction failed: {result.get('error', 'Unknown error')}"
                
                # Send notification
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Date Correction Complete",
                        "message": message,
                        "notification_id": "ev_date_correction"
                    }
                )
                
            except Exception as e:
                _LOGGER.error("Error in date correction service: %s", e)
                await hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "EV Date Correction Failed",
                        "message": f"Error: {str(e)}",
                        "notification_id": "ev_date_correction_error"
                    }
                )
        
        # Register the service
        hass.services.async_register(
            "ev_charging_extractor", 
            "fix_receipt_dates", 
            fix_receipt_dates_service
        )
        
        _LOGGER.info("Date correction service registered")


# Example usage in your EV processor
def add_date_correction_to_processor(processor):
    """Add date correction functionality to existing processor."""
    
    # Create date corrector instance
    date_corrector = DateCorrector(processor.db_path)
    
    # Add method to processor
    def fix_receipt_dates(self):
        """Fix incorrect dates in existing receipts."""
        return date_corrector.fix_receipt_dates()
    
    def analyze_date_issues(self):
        """Analyze receipts with date issues."""
        return date_corrector.analyze_date_issues()
    
    # Monkey patch the methods onto the processor
    processor.fix_receipt_dates = fix_receipt_dates.__get__(processor, processor.__class__)
    processor.analyze_date_issues = analyze_date_issues.__get__(processor, processor.__class__)
    
    return processor