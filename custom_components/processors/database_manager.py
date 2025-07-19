"""Database manager for EV charging data."""
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..models import ChargingReceipt

_LOGGER = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database operations for EV charging data."""
    
    def __init__(self, db_path: str):
        """Initialize database manager."""
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Initialize SQLite database with required tables."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create main table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS charging_receipts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    date TEXT NOT NULL,
                    location TEXT NOT NULL,
                    cost REAL NOT NULL,
                    currency TEXT NOT NULL,
                    energy_kwh REAL,
                    session_duration TEXT,
                    email_subject TEXT,
                    raw_data TEXT,
                    source_type TEXT DEFAULT 'email',
                    hash_id TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create processed items tracking tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_hash TEXT UNIQUE NOT NULL,
                    email_subject TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_evcc_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_hash TEXT UNIQUE NOT NULL,
                    session_data TEXT,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash_id ON charging_receipts(hash_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_provider_date ON charging_receipts(provider, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_type ON charging_receipts(source_type)')
            
            conn.commit()
            conn.close()
            
            _LOGGER.info("Database initialized at: %s", self.db_path)
        except Exception as e:
            _LOGGER.error("Failed to setup database: %s", e)
    
    def is_duplicate_receipt(self, receipt: ChargingReceipt, source_type: str = 'email') -> bool:
        """Check if receipt is duplicate."""
        try:
            receipt_hash = receipt.generate_hash(source_type)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM charging_receipts WHERE hash_id = ?', (receipt_hash,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
        except Exception as e:
            _LOGGER.error("Error checking duplicate: %s", e)
            return False
    
    def save_receipt(self, receipt: ChargingReceipt, source_type: str = 'email', minimum_cost: float = 0.0) -> bool:
        """Save receipt to database."""
        try:
            # Validate receipt
            if not receipt.is_valid(minimum_cost):
                _LOGGER.debug("Skipping invalid receipt: %s", receipt)
                return False
            
            # Check for duplicates
            if self.is_duplicate_receipt(receipt, source_type):
                _LOGGER.debug("Skipping duplicate receipt: %s", receipt)
                return False
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            receipt_hash = receipt.generate_hash(source_type)
            
            cursor.execute('''
                INSERT INTO charging_receipts 
                (provider, date, location, cost, currency, energy_kwh, session_duration, 
                 email_subject, raw_data, source_type, hash_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                receipt.provider,
                receipt.date.isoformat(),
                receipt.location,
                receipt.cost,
                receipt.currency,
                receipt.energy_kwh,
                receipt.session_duration,
                receipt.email_subject,
                receipt.raw_data,
                source_type,
                receipt_hash
            ))
            
            conn.commit()
            conn.close()
            
            _LOGGER.info("Saved receipt: %s", receipt)
            return True
            
        except Exception as e:
            _LOGGER.error("Error saving receipt: %s", e)
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_receipts,
                    COALESCE(SUM(cost), 0) as total_cost,
                    COALESCE(SUM(energy_kwh), 0) as total_energy
                FROM charging_receipts
            ''')
            totals = cursor.fetchone()
            
            # Monthly statistics (last 30 days)
            cursor.execute('''
                SELECT 
                    COUNT(*) as monthly_receipts,
                    COALESCE(SUM(cost), 0) as monthly_cost,
                    COALESCE(SUM(energy_kwh), 0) as monthly_energy
                FROM charging_receipts
                WHERE date >= date('now', '-30 days')
            ''')
            monthly = cursor.fetchone()
            
            # Home vs Public charging (monthly)
            cursor.execute('''
                SELECT 
                    COUNT(*) as home_monthly_receipts,
                    COALESCE(SUM(cost), 0) as home_monthly_cost,
                    COALESCE(SUM(energy_kwh), 0) as home_monthly_energy
                FROM charging_receipts
                WHERE date >= date('now', '-30 days') AND source_type = 'evcc'
            ''')
            home_monthly = cursor.fetchone()
            
            cursor.execute('''
                SELECT 
                    COUNT(*) as public_monthly_receipts,
                    COALESCE(SUM(cost), 0) as public_monthly_cost,
                    COALESCE(SUM(energy_kwh), 0) as public_monthly_energy
                FROM charging_receipts
                WHERE date >= date('now', '-30 days') AND source_type = 'email'
            ''')
            public_monthly = cursor.fetchone()
            
            # Last session
            cursor.execute('''
                SELECT provider, cost, energy_kwh, date
                FROM charging_receipts
                ORDER BY date DESC
                LIMIT 1
            ''')
            last_session = cursor.fetchone()
            
            # Top provider
            cursor.execute('''
                SELECT provider, COUNT(*) as count
                FROM charging_receipts
                GROUP BY provider
                ORDER BY count DESC
                LIMIT 1
            ''')
            top_provider = cursor.fetchone()
            
            conn.close()
            
            # Build statistics dictionary
            stats = {
                'total_receipts': totals[0] if totals else 0,
                'total_cost': totals[1] if totals else 0.0,
                'total_energy': totals[2] if totals else 0.0,
                'monthly_receipts': monthly[0] if monthly else 0,
                'monthly_cost': monthly[1] if monthly else 0.0,
                'monthly_energy': monthly[2] if monthly else 0.0,
                'home_monthly_receipts': home_monthly[0] if home_monthly else 0,
                'home_monthly_cost': home_monthly[1] if home_monthly else 0.0,
                'home_monthly_energy': home_monthly[2] if home_monthly else 0.0,
                'public_monthly_receipts': public_monthly[0] if public_monthly else 0,
                'public_monthly_cost': public_monthly[1] if public_monthly else 0.0,
                'public_monthly_energy': public_monthly[2] if public_monthly else 0.0,
            }
            
            # Calculate averages
            if stats['total_energy'] > 0:
                stats['average_cost_per_kwh'] = stats['total_cost'] / stats['total_energy']
            else:
                stats['average_cost_per_kwh'] = 0.0
            
            # Last session info
            if last_session:
                stats['last_session_provider'] = last_session[0]
                stats['last_session_cost'] = last_session[1]
                stats['last_session_energy'] = last_session[2]
                stats['last_session_date'] = last_session[3]
            else:
                stats['last_session_provider'] = 'None'
                stats['last_session_cost'] = 0.0
                stats['last_session_energy'] = 0.0
                stats['last_session_date'] = None
            
            # Top provider
            if top_provider:
                stats['top_provider'] = top_provider[0]
            else:
                stats['top_provider'] = 'None'
            
            return stats
            
        except Exception as e:
            _LOGGER.error("Error getting database stats: %s", e)
            return {}
    
    def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get count before clearing
            cursor.execute('SELECT COUNT(*) FROM charging_receipts')
            receipt_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM processed_emails')
            email_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM processed_evcc_sessions')
            session_count = cursor.fetchone()[0]
            
            # Clear all tables
            cursor.execute('DELETE FROM charging_receipts')
            cursor.execute('DELETE FROM processed_emails')
            cursor.execute('DELETE FROM processed_evcc_sessions')
            
            # Reset auto-increment counters
            cursor.execute('DELETE FROM sqlite_sequence WHERE name IN ("charging_receipts", "processed_emails", "processed_evcc_sessions")')
            
            conn.commit()
            conn.close()
            
            _LOGGER.info("Cleared all data: %d receipts, %d processed emails, %d EVCC sessions", 
                        receipt_count, email_count, session_count)
            
            return {
                'success': True,
                'receipts_cleared': receipt_count,
                'emails_cleared': email_count,
                'sessions_cleared': session_count
            }
            
        except Exception as e:
            _LOGGER.error("Error clearing data: %s", e)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_all_receipts(self) -> List[Dict[str, Any]]:
        """Get all receipts for export."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Use row factory to get dict-like results
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    provider,
                    date,
                    location,
                    cost,
                    currency,
                    energy_kwh,
                    session_duration,
                    source_type,
                    created_at
                FROM charging_receipts
                ORDER BY date DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to list of dicts
            return [dict(row) for row in rows]
            
        except Exception as e:
            _LOGGER.error("Error getting receipts for export: %s", e)
            return []
    
    def mark_email_processed(self, email_hash: str, subject: str = "") -> bool:
        """Mark an email as processed."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO processed_emails (email_hash, email_subject)
                VALUES (?, ?)
            ''', (email_hash, subject))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            _LOGGER.error("Error marking email as processed: %s", e)
            return False
    
    def is_email_processed(self, email_hash: str) -> bool:
        """Check if an email has been processed."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM processed_emails WHERE email_hash = ?', (email_hash,))
            result = cursor.fetchone()
            
            conn.close()
            return result is not None
            
        except Exception as e:
            _LOGGER.error("Error checking if email processed: %s", e)
            return False
