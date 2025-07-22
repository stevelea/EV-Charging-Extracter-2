"""EVCC processor for home charging data."""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None

from ..models import ChargingReceipt
from .database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class EVCCProcessor:
    """Handles EVCC home charging data processing."""
    
    def __init__(self, evcc_url: str, evcc_enabled: bool, home_electricity_rate: float,
                 database_manager: DatabaseManager, default_currency: str = "AUD", 
                 verbose_logging: bool = False):
        """Initialize EVCC processor."""
        self.evcc_url = evcc_url
        self.evcc_enabled = evcc_enabled
        self.home_electricity_rate = home_electricity_rate
        self.database_manager = database_manager
        self.default_currency = default_currency
        self.verbose_logging = verbose_logging
    
    def process_sessions(self) -> Dict[str, Any]:
        """Process EVCC sessions and save to database."""
        results = {
            'new_sessions': 0,
            'errors': []
        }
        
        if not self.evcc_enabled:
            if self.verbose_logging:
                _LOGGER.debug("EVCC processing disabled")
            return results
        
        try:
            sessions = self.get_sessions()
            
            for session in sessions:
                try:
                    if self.database_manager.save_receipt(session, 'evcc'):
                        results['new_sessions'] += 1
                        _LOGGER.info("Successfully processed EVCC session: %.2f kWh, $%.2f", 
                                   session.energy_kwh or 0, session.cost)
                except Exception as e:
                    _LOGGER.error("Error saving EVCC session: %s", e)
                    results['errors'].append(f"EVCC session error: {str(e)}")
            
        except Exception as e:
            _LOGGER.error("Error processing EVCC sessions: %s", e)
            results['errors'].append(f"EVCC processing error: {str(e)}")
        
        return results
    
    def get_sessions(self) -> List[ChargingReceipt]:
        """Get charging sessions from EVCC."""
        if not self.evcc_enabled:
            return []
        
        try:
            if not requests:
                _LOGGER.error("Requests library not available for EVCC")
                return []
            
            _LOGGER.info("🔌 Fetching EVCC sessions from: %s", self.evcc_url)
            
            endpoint = f"{self.evcc_url}/api/sessions"
            
            try:
                response = requests.get(endpoint, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if self.verbose_logging:
                        _LOGGER.debug("EVCC response preview: %s", str(data)[:500])
                    
                    # Extract sessions from result array
                    sessions_data = []
                    if isinstance(data, dict) and 'result' in data:
                        sessions_data = data['result']
                    elif isinstance(data, list):
                        sessions_data = data
                    else:
                        _LOGGER.warning("Unexpected EVCC response format: %s", type(data))
                        return []
                    
                    _LOGGER.info("📊 Found %d sessions in EVCC data", len(sessions_data))
                    
                    # Process the sessions
                    processed_sessions = []
                    for session_data in sessions_data:
                        try:
                            receipt = self._process_session_data(session_data)
                            if receipt:
                                processed_sessions.append(receipt)
                        except Exception as e:
                            _LOGGER.warning("Error processing EVCC session %s: %s", 
                                          session_data.get('id', 'unknown'), e)
                            continue
                    
                    _LOGGER.info("✅ Processed %d valid EVCC sessions", len(processed_sessions))
                    return processed_sessions
                
                else:
                    _LOGGER.error("EVCC endpoint returned status %d: %s", 
                                response.status_code, response.text[:200])
                    return []
                    
            except requests.exceptions.RequestException as e:
                _LOGGER.error("EVCC connection failed: %s", e)
                return []
            except Exception as e:
                _LOGGER.error("Error parsing EVCC response: %s", e)
                return []
            
        except Exception as e:
            _LOGGER.error("Error getting EVCC sessions: %s", e)
            return []
    
    def _process_session_data(self, session_data: Dict[str, Any]) -> Optional[ChargingReceipt]:
        """Process EVCC session data into a ChargingReceipt."""
        try:
            if not isinstance(session_data, dict):
                return None
            
            session_id = session_data.get('id', 'unknown')
            
            # Extract energy
            energy_kwh = session_data.get('chargedEnergy')
            if not energy_kwh or energy_kwh <= 0:
                if self.verbose_logging:
                    _LOGGER.debug("Skipping EVCC session %s - no valid energy data (%.2f kWh)", 
                                session_id, energy_kwh or 0)
                return None
            
            # Calculate cost
            if 'price' in session_data and session_data['price'] is not None:
                cost = float(session_data['price'])
            else:
                cost = energy_kwh * self.home_electricity_rate
            
            # Extract timestamps
            session_date = datetime.now()
            for timestamp_field in ['finished', 'created']:
                if timestamp_field in session_data and session_data[timestamp_field]:
                    try:
                        timestamp_str = session_data[timestamp_field]
                        session_date = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        break
                    except Exception:
                        continue
            
            # Extract duration
            session_duration = None
            if 'chargeDuration' in session_data and session_data['chargeDuration']:
                try:
                    duration_ns = session_data['chargeDuration']
                    duration_seconds = duration_ns / 1_000_000_000
                    
                    hours = int(duration_seconds // 3600)
                    minutes = int((duration_seconds % 3600) // 60)
                    
                    if hours > 0:
                        session_duration = f"{hours}h {minutes}m"
                    else:
                        session_duration = f"{minutes}m"
                except Exception:
                    pass
            
            # Build location info
            location_parts = ["Home Charging"]
            
            if 'loadpoint' in session_data and session_data['loadpoint']:
                location_parts.append(f"({session_data['loadpoint']})")
            
            if 'vehicle' in session_data and session_data['vehicle']:
                location_parts.append(f"- {session_data['vehicle']}")
            
            location = " ".join(location_parts)
            
            # Additional info for email subject
            solar_info = ""
            if 'solarPercentage' in session_data and session_data['solarPercentage'] is not None:
                solar_pct = session_data['solarPercentage']
                solar_info = f" (Solar: {solar_pct:.1f}%)"
            
            price_info = ""
            if 'pricePerKWh' in session_data and session_data['pricePerKWh'] is not None:
                price_per_kwh = session_data['pricePerKWh']
                price_info = f" @${price_per_kwh:.4f}/kWh"
            
            # Create receipt
            receipt = ChargingReceipt(
                provider="EVCC (Home)",
                date=session_date,
                location=location,
                cost=cost,
                currency=self.default_currency,
                energy_kwh=energy_kwh,
                session_duration=session_duration,
                email_subject=f"EVCC Home Charging Session #{session_id}{solar_info}{price_info}",
                raw_data=str(session_data)[:1000]
            )
            
            if self.verbose_logging:
                _LOGGER.info("EVCC session #%s processed: %.2f kWh, $%.2f, %s%s", 
                            session_id, energy_kwh, cost, session_date.strftime('%Y-%m-%d %H:%M'), solar_info)
            
            return receipt
            
        except Exception as e:
            _LOGGER.error("Error processing EVCC session data: %s", e)
            return None
    
    def debug_connection(self):
        """Debug EVCC connection and data structure."""
        _LOGGER.info("🔍 EVCC Debug - Starting connection test")
        
        if not self.evcc_enabled:
            _LOGGER.error("❌ EVCC is disabled in configuration")
            return
        
        if not requests:
            _LOGGER.error("❌ Requests library not available")
            return
        
        _LOGGER.info("🔌 EVCC URL: %s", self.evcc_url)
        _LOGGER.info("🏠 Home electricity rate: $%.4f/kWh", self.home_electricity_rate)
        
        # Test multiple endpoints
        endpoints_to_test = [
            "/api/state",
            "/api/sessions", 
            "/api/session",
            "/api/log",
            "/api/config",
            "/api/health",
            "/api/version",
        ]
        
        for endpoint in endpoints_to_test:
            full_url = f"{self.evcc_url}{endpoint}"
            try:
                _LOGGER.info("🔍 Testing endpoint: %s", full_url)
                response = requests.get(full_url, timeout=10)
                
                _LOGGER.info("📊 Status: %d, Content-Length: %d", 
                           response.status_code, len(response.content))
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        _LOGGER.info("✅ JSON Response Structure:")
                        self._log_json_structure(data, prefix="  ")
                        
                        # Look for charging data specifically
                        if endpoint == '/api/sessions' and isinstance(data, list):
                            _LOGGER.info("🔍 Found %d sessions in /api/sessions", len(data))
                            for i, session in enumerate(data[:3]):
                                _LOGGER.info("  Session %d: %s", i, str(session)[:200])
                        
                    except ValueError as e:
                        _LOGGER.warning("❌ Invalid JSON response: %s", e)
                        _LOGGER.info("Raw response: %s", response.text[:500])
                else:
                    _LOGGER.warning("❌ HTTP %d: %s", response.status_code, response.text[:200])
                    
            except requests.exceptions.ConnectionError:
                _LOGGER.error("❌ Connection failed to %s - Is EVCC running?", full_url)
            except requests.exceptions.Timeout:
                _LOGGER.error("❌ Timeout connecting to %s", full_url)
            except Exception as e:
                _LOGGER.error("❌ Error testing %s: %s", full_url, e)
        
        _LOGGER.info("🏁 EVCC Debug complete")
    
    def _log_json_structure(self, data, prefix="", max_depth=3):
        """Log the structure of JSON data for debugging."""
        if max_depth <= 0:
            return
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    _LOGGER.info("%s%s: %s (%d items)", prefix, key, type(value).__name__, len(value))
                    self._log_json_structure(value, prefix + "  ", max_depth - 1)
                else:
                    _LOGGER.info("%s%s: %s = %s", prefix, key, type(value).__name__, str(value)[:50])
        elif isinstance(data, list):
            _LOGGER.info("%sList with %d items", prefix, len(data))
            if data and max_depth > 1:
                _LOGGER.info("%sFirst item:", prefix)
                self._log_json_structure(data[0], prefix + "  ", max_depth - 1)
