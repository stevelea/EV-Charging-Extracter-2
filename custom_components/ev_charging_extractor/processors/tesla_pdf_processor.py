"""Tesla PDF processor for processing Tesla receipt PDFs."""
import os
import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import hashlib

try:
    import PyPDF2
    import pandas as pd
except ImportError:
    PyPDF2 = None
    pd = None

from ..models import ChargingReceipt
from .database_manager import DatabaseManager

_LOGGER = logging.getLogger(__name__)


class TeslaPDFProcessor:
    """Processes Tesla PDF receipts from the www/Tesla directory."""
    
    def __init__(self, hass_config_path: str, database_manager: DatabaseManager, 
                 default_currency: str = "AUD", verbose_logging: bool = False):
        """Initialize Tesla PDF processor."""
        self.hass_config_path = hass_config_path
        self.database_manager = database_manager
        self.default_currency = default_currency
        self.verbose_logging = verbose_logging
        self.tesla_dir = os.path.join(hass_config_path, "www", "Tesla")
        
        # Ensure Tesla directory exists
        os.makedirs(self.tesla_dir, exist_ok=True)
    
    def process_tesla_pdfs(self) -> Dict[str, Any]:
        """Process all Tesla PDF receipts in the Tesla directory."""
        results = {
            'new_tesla_receipts': 0,
            'processed_files': [],
            'errors': []
        }
        
        if not PyPDF2:
            error_msg = "PyPDF2 not available - cannot process Tesla PDFs"
            _LOGGER.error(error_msg)
            results['errors'].append(error_msg)
            return results
        
        try:
            _LOGGER.info("🚗 Starting Tesla PDF processing from: %s", self.tesla_dir)
            
            # Find all PDF files in Tesla directory and subdirectories
            pdf_files = self._find_tesla_pdfs()
            
            _LOGGER.info("Found %d Tesla PDF files to process", len(pdf_files))
            
            for pdf_path in pdf_files:
                try:
                    # Check if this PDF has already been processed
                    if self._is_pdf_already_processed(pdf_path):
                        if self.verbose_logging:
                            _LOGGER.debug("Skipping already processed PDF: %s", os.path.basename(pdf_path))
                        continue
                    
                    # Extract text from PDF
                    pdf_text = self._extract_pdf_text(pdf_path)
                    
                    if not pdf_text:
                        _LOGGER.warning("Could not extract text from PDF: %s", pdf_path)
                        continue
                    
                    # Parse Tesla receipt data
                    receipt = self._parse_tesla_receipt(pdf_text, pdf_path)
                    
                    if receipt:
                        # Save receipt to database
                        if self.database_manager.save_receipt(receipt, 'tesla_pdf'):
                            results['new_tesla_receipts'] += 1
                            results['processed_files'].append(os.path.basename(pdf_path))
                            
                            _LOGGER.info("✅ Tesla receipt processed: %s - $%.2f at %s", 
                                       os.path.basename(pdf_path), receipt.cost, receipt.location)
                            
                            # Mark PDF as processed
                            self._mark_pdf_processed(pdf_path)
                        else:
                            if self.verbose_logging:
                                _LOGGER.debug("Tesla receipt not saved (duplicate or invalid): %s", 
                                            os.path.basename(pdf_path))
                    else:
                        _LOGGER.warning("Could not parse Tesla receipt from: %s", pdf_path)
                        
                except Exception as e:
                    error_msg = f"Error processing Tesla PDF {os.path.basename(pdf_path)}: {str(e)}"
                    _LOGGER.error(error_msg)
                    results['errors'].append(error_msg)
            
            _LOGGER.info("🏁 Tesla PDF processing complete: %d new receipts", results['new_tesla_receipts'])
            
        except Exception as e:
            error_msg = f"Error in Tesla PDF processing: {str(e)}"
            _LOGGER.error(error_msg)
            results['errors'].append(error_msg)
        
        return results
    
    def _find_tesla_pdfs(self) -> List[str]:
        """Find all Tesla PDF files in the Tesla directory."""
        pdf_files = []
        
        try:
            for root, dirs, files in os.walk(self.tesla_dir):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        pdf_path = os.path.join(root, file)
                        pdf_files.append(pdf_path)
        except Exception as e:
            _LOGGER.error("Error finding Tesla PDFs: %s", e)
        
        return pdf_files
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from Tesla PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                    except Exception as e:
                        _LOGGER.warning("Error extracting text from page in %s: %s", pdf_path, e)
                        continue
                
                return text.strip()
                
        except Exception as e:
            _LOGGER.error("Error extracting text from Tesla PDF %s: %s", pdf_path, e)
            return ""
    
    def _parse_tesla_receipt(self, text: str, pdf_path: str) -> Optional[ChargingReceipt]:
        """Parse Tesla receipt text into a ChargingReceipt object."""
        try:
            if self.verbose_logging:
                _LOGGER.debug("Parsing Tesla receipt from: %s", os.path.basename(pdf_path))
                _LOGGER.debug("PDF text preview: %s", text[:500])
            
            # Extract invoice number for tracking
            invoice_number = self._extract_invoice_number(text)
            
            # Extract date
            invoice_date = self._extract_date(text)
            if not invoice_date:
                _LOGGER.warning("Could not extract date from Tesla PDF: %s", pdf_path)
                return None
            
            # Extract charging location
            location = self._extract_location(text)
            if not location:
                _LOGGER.warning("Could not extract location from Tesla PDF: %s", pdf_path)
                return None
            
            # Extract cost (Total Amount)
            cost = self._extract_cost(text)
            if not cost or cost <= 0:
                _LOGGER.warning("Could not extract valid cost from Tesla PDF: %s", pdf_path)
                return None
            
            # Extract energy (kWh)
            energy_kwh = self._extract_energy(text)
            
            # Extract unit price for additional info
            unit_price = self._extract_unit_price(text)
            
            # Build email subject for consistency with other sources
            subject = f"Tesla Supercharging Receipt - {invoice_number or 'Unknown'}"
            if unit_price:
                subject += f" @${unit_price:.3f}/kWh"
            
            # Create receipt
            receipt = ChargingReceipt(
                provider="Tesla",
                date=invoice_date,
                location=location,
                cost=cost,
                currency=self.default_currency,
                energy_kwh=energy_kwh,
                session_duration=None,  # Tesla PDFs don't typically include duration
                email_subject=subject,
                raw_data=text[:2000]  # Store first 2000 chars for debugging
            )
            
            if self.verbose_logging:
                _LOGGER.debug("Parsed Tesla receipt: %s", receipt)
            
            return receipt
            
        except Exception as e:
            _LOGGER.error("Error parsing Tesla receipt from %s: %s", pdf_path, e)
            return None
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract Tesla invoice number."""
        patterns = [
            r'Invoice\s+Number\s+([A-Z0-9]+)',
            r'Invoice\s+Number:\s*([A-Z0-9]+)',
            r'Invoice\s*#\s*([A-Z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_date(self, text: str) -> Optional[datetime]:
        """Extract date from Tesla receipt."""
        patterns = [
            r'Invoice\s+date\s+(\d{4}/\d{2}/\d{2})',  # 2025/02/09
            r'Date\s+of\s+Event[^\n]*(\d{4}/\d{2}/\d{2})',  # Date of Event ... 2025/02/09
            r'(\d{4}/\d{2}/\d{2})',  # Standalone date
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    # Tesla uses YYYY/MM/DD format
                    invoice_date = datetime.strptime(date_str, '%Y/%m/%d')
                    if self.verbose_logging:
                        _LOGGER.debug("Found Tesla date: %s -> %s", date_str, invoice_date)
                    return invoice_date
                except ValueError as e:
                    if self.verbose_logging:
                        _LOGGER.debug("Date parsing failed for '%s': %s", date_str, e)
                    continue
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract Tesla charging location."""
        patterns = [
            # Tesla specific location patterns
            r'Charging\s+Location\s*\n\s*([^\n]+)\s*\n\s*([^\n]+)\s*\n\s*([^\n]+)',  # Multi-line location
            r'Charging\s+Location[:\s]*([^\n]+(?:\n[^\n]+)*?)(?:\n\s*S/N:|$)',  # Location until S/N
            r'([A-Za-z\s]+,\s*[A-Z]{2,3})\s*\n\s*([^\n]+)\s*\n\s*(\d{4}\s+[A-Za-z\s]+)',  # City, STATE \n Address \n Postcode Location
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                if len(match.groups()) > 1:
                    # Combine multiple groups for full location
                    location_parts = [group.strip() for group in match.groups() if group and group.strip()]
                    location = ', '.join(location_parts)
                else:
                    location = match.group(1).strip()
                
                # Clean up the location
                location = location.replace('\n', ', ')
                location = re.sub(r'\s+', ' ', location)  # Normalize whitespace
                location = re.sub(r',\s*,', ',', location)  # Remove double commas
                location = location[:200]  # Limit length
                
                if location and len(location) > 5:
                    if self.verbose_logging:
                        _LOGGER.debug("Found Tesla location: %s", location)
                    return location
        
        return None
    
    def _extract_cost(self, text: str) -> Optional[float]:
        """Extract total cost from Tesla receipt."""
        patterns = [
            r'Total\s+Amount\s+\(AUD\)\s+([0-9]+\.[0-9]{2})',  # Total Amount (AUD) 14.93
            r'Total\s+Amount[:\s]*\$?([0-9]+\.[0-9]{2})',  # Total Amount: 14.93
            r'Total[:\s]*\$?([0-9]+\.[0-9]{2})\s*AUD',  # Total: 14.93 AUD
            r'Total[:\s]*([0-9]+\.[0-9]{2})',  # Total: 14.93
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cost_value = float(match.group(1))
                    if cost_value > 0:
                        if self.verbose_logging:
                            _LOGGER.debug("Found Tesla cost: $%.2f", cost_value)
                        return cost_value
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_energy(self, text: str) -> Optional[float]:
        """Extract energy (kWh) from Tesla receipt."""
        patterns = [
            r'([0-9]+\.[0-9]+)\s*kWh',  # 19.3930 kWh
            r'(\d+\.\d+)\s*kWh\s+10',  # Energy amount before GST percentage
            r'Energy\s+fee[^\n]*([0-9]+\.[0-9]+)\s*kWh',  # Energy fee ... 19.3930 kWh
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    energy_value = float(match.group(1))
                    if 0 < energy_value < 200:  # Reasonable range
                        if self.verbose_logging:
                            _LOGGER.debug("Found Tesla energy: %.4f kWh", energy_value)
                        return energy_value
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_unit_price(self, text: str) -> Optional[float]:
        """Extract unit price per kWh from Tesla receipt."""
        patterns = [
            r'Energy\s+fee\s+([0-9]+\.[0-9]+)\s*/\s*kWh',  # Energy fee 0.70 / kWh
            r'([0-9]+\.[0-9]+)\s*/\s*kWh',  # 0.70 / kWh
            r'\$([0-9]+\.[0-9]+)\s*per\s*kWh',  # $0.70 per kWh
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    unit_price = float(match.group(1))
                    if 0 < unit_price < 5:  # Reasonable range for $/kWh
                        if self.verbose_logging:
                            _LOGGER.debug("Found Tesla unit price: $%.3f/kWh", unit_price)
                        return unit_price
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _is_pdf_already_processed(self, pdf_path: str) -> bool:
        """Check if PDF has already been processed."""
        try:
            pdf_hash = self._get_pdf_hash(pdf_path)
            return self.database_manager.is_tesla_pdf_processed(pdf_hash)
        except Exception as e:
            _LOGGER.error("Error checking if PDF processed: %s", e)
            return False
    
    def _mark_pdf_processed(self, pdf_path: str) -> bool:
        """Mark PDF as processed."""
        try:
            pdf_hash = self._get_pdf_hash(pdf_path)
            filename = os.path.basename(pdf_path)
            return self.database_manager.mark_tesla_pdf_processed(pdf_hash, filename)
        except Exception as e:
            _LOGGER.error("Error marking PDF as processed: %s", e)
            return False
    
    def _get_pdf_hash(self, pdf_path: str) -> str:
        """Generate hash for PDF file."""
        try:
            with open(pdf_path, 'rb') as f:
                file_content = f.read()
                return hashlib.sha256(file_content).hexdigest()[:16]
        except Exception as e:
            _LOGGER.error("Error generating PDF hash: %s", e)
            return hashlib.sha256(pdf_path.encode()).hexdigest()[:16]
    
    def debug_tesla_pdfs(self):
        """Debug function to analyze Tesla PDF structure."""
        try:
            pdf_files = self._find_tesla_pdfs()
            _LOGGER.info("🔍 Tesla PDF Debug - Found %d PDF files", len(pdf_files))
            
            for i, pdf_path in enumerate(pdf_files[:3]):  # Debug first 3 PDFs
                _LOGGER.info("=== DEBUG TESLA PDF %d: %s ===", i+1, os.path.basename(pdf_path))
                
                # Extract text
                text = self._extract_pdf_text(pdf_path)
                if text:
                    _LOGGER.info("PDF text length: %d characters", len(text))
                    _LOGGER.info("PDF text preview: %s", text[:1000])
                    
                    # Try to extract each field
                    invoice_number = self._extract_invoice_number(text)
                    date = self._extract_date(text)
                    location = self._extract_location(text)
                    cost = self._extract_cost(text)
                    energy = self._extract_energy(text)
                    unit_price = self._extract_unit_price(text)
                    
                    _LOGGER.info("Extracted fields:")
                    _LOGGER.info("  Invoice Number: %s", invoice_number)
                    _LOGGER.info("  Date: %s", date)
                    _LOGGER.info("  Location: %s", location)
                    _LOGGER.info("  Cost: $%.2f", cost or 0)
                    _LOGGER.info("  Energy: %.4f kWh", energy or 0)
                    _LOGGER.info("  Unit Price: $%.3f/kWh", unit_price or 0)
                else:
                    _LOGGER.warning("Could not extract text from PDF")
                    
        except Exception as e:
            _LOGGER.error("Error in Tesla PDF debug: %s", e)