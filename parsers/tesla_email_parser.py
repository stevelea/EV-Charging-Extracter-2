"""Simple Tesla email parser for processing Tesla charging emails with multiple PDFs."""
import re
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import email
import hashlib

try:
    import PyPDF2
    import io
except ImportError:
    PyPDF2 = None
    io = None

from .base_parser import BaseParser
from ..models import ChargingReceipt

_LOGGER = logging.getLogger(__name__)


class TeslaEmailParser(BaseParser):
    """Simple parser for Tesla charging emails containing multiple PDF receipts."""
    
    def get_provider_name(self) -> str:
        """Return the provider name."""
        return "Tesla"
    
    def can_parse(self, sender: str, subject: str) -> bool:
        """Check if this parser can handle the email."""
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        
        # Check for specific Tesla email pattern from stevelea@gmail.com
        return (
            'stevelea@gmail.com' in sender_lower and 
            'tesla charging' in subject_lower
        )
    
    def parse_receipt(self, email_data: Dict[str, any]) -> Optional[ChargingReceipt]:
        """Parse single receipt - returns first Tesla receipt found."""
        receipts = self.parse_email_with_pdfs(email_data)
        return receipts[0] if receipts else None
    
    def parse_email_with_pdfs(self, email_data: Dict[str, any]) -> List[ChargingReceipt]:
        """Parse Tesla email and extract all PDF receipts."""
        receipts = []
        
        if not PyPDF2:
            _LOGGER.error("PyPDF2 not available - cannot process Tesla PDF attachments")
            return receipts
        
        try:
            # Get raw email content to extract PDFs
            raw_email = email_data.get('raw_email')
            if not raw_email:
                _LOGGER.warning("No raw email data available for Tesla PDF extraction")
                return receipts
            
            # Parse email to get PDF attachments
            pdf_attachments = self._extract_pdf_attachments(raw_email)
            
            if not pdf_attachments:
                _LOGGER.warning("No PDF attachments found in Tesla email")
                return receipts
            
            _LOGGER.info("Processing Tesla email with %d PDF attachments", len(pdf_attachments))
            
            # Process each PDF attachment
            for i, pdf_info in enumerate(pdf_attachments):
                try:
                    if self.verbose_logging:
                        _LOGGER.debug("Processing Tesla PDF attachment %d/%d: %s", 
                                    i+1, len(pdf_attachments), pdf_info['filename'])
                    
                    # Extract text from PDF
                    pdf_text = self._extract_pdf_text(pdf_info['content'])
                    
                    if not pdf_text:
                        _LOGGER.warning("Could not extract text from Tesla PDF attachment %d", i+1)
                        continue
                    
                    # Parse Tesla receipt from PDF text
                    receipt = self._parse_tesla_receipt_from_text(
                        pdf_text, 
                        pdf_info['filename'],
                        email_data
                    )
                    
                    if receipt:
                        receipts.append(receipt)
                        _LOGGER.info("✅ Parsed Tesla receipt %d: $%.2f at %s", 
                                   i+1, receipt.cost, receipt.location)
                    else:
                        _LOGGER.warning("Could not parse Tesla receipt from PDF %d", i+1)
                        
                except Exception as e:
                    _LOGGER.error("Error processing Tesla PDF attachment %d: %s", i+1, e)
                    continue
            
            _LOGGER.info("Successfully processed %d Tesla receipts from email", len(receipts))
            return receipts
            
        except Exception as e:
            _LOGGER.error("Error parsing Tesla email with PDFs: %s", e)
            return receipts
    
    def _extract_pdf_attachments(self, raw_email: bytes) -> List[Dict[str, any]]:
        """Extract PDF attachments from raw email."""
        pdf_attachments = []
        
        try:
            msg = email.message_from_bytes(raw_email)
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    if content_type == "application/pdf":
                        filename = part.get_filename()
                        if filename:
                            try:
                                pdf_data = part.get_payload(decode=True)
                                if pdf_data:
                                    pdf_attachments.append({
                                        'filename': filename,
                                        'content': pdf_data,
                                        'size': len(pdf_data)
                                    })
                                    
                                    if self.verbose_logging:
                                        _LOGGER.debug("Found Tesla PDF attachment: %s (%d bytes)", 
                                                    filename, len(pdf_data))
                            except Exception as e:
                                _LOGGER.warning("Error extracting Tesla PDF attachment %s: %s", filename, e)
            
            return pdf_attachments
            
        except Exception as e:
            _LOGGER.error("Error extracting PDF attachments from Tesla email: %s", e)
            return []
    
    def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            pdf_file = io.BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    _LOGGER.warning("Error extracting text from Tesla PDF page: %s", e)
                    continue
            
            return text.strip()
            
        except Exception as e:
            _LOGGER.error("Error extracting text from Tesla PDF: %s", e)
            return ""
    
    def _parse_tesla_receipt_from_text(self, text: str, filename: str, email_data: Dict[str, any]) -> Optional[ChargingReceipt]:
        """Parse Tesla receipt text into a ChargingReceipt object."""
        try:
            if self.verbose_logging:
                _LOGGER.debug("Parsing Tesla receipt from: %s", filename)
                _LOGGER.debug("PDF text preview: %s", text[:500])
            
            # Extract invoice number for tracking
            invoice_number = self._extract_invoice_number(text)
            
            # Extract date
            invoice_date = self._extract_date(text)
            if not invoice_date:
                _LOGGER.warning("Could not extract date from Tesla PDF: %s", filename)
                return None
            
            # Extract charging location
            location = self._extract_location(text)
            if not location:
                _LOGGER.warning("Could not extract location from Tesla PDF: %s", filename)
                return None
            
            # Extract cost (Total Amount)
            cost = self._extract_cost(text)
            if not cost or cost <= 0:
                _LOGGER.warning("Could not extract valid cost from Tesla PDF: %s", filename)
                return None
            
            # Extract energy (kWh)
            energy_kwh = self._extract_energy(text)
            
            # Extract unit price for additional info
            unit_price = self._extract_unit_price(text)
            
            # Build email subject for consistency with other sources
            subject = f"Tesla Supercharging Receipt - {invoice_number or 'Unknown'}"
            if unit_price:
                subject += f" @${unit_price:.3f}/kWh"
            
            # Add original email info to raw data
            email_info = f"From: {email_data.get('sender', 'Unknown')}, Subject: {email_data.get('subject', 'Unknown')}, PDF: {filename}"
            raw_data_with_email = f"{email_info}\n\n{text[:1800]}"  # Include email info + PDF text
            
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
                raw_data=raw_data_with_email
            )
            
            if self.verbose_logging:
                _LOGGER.debug("Parsed Tesla receipt: %s", receipt)
            
            return receipt
            
        except Exception as e:
            _LOGGER.error("Error parsing Tesla receipt from %s: %s", filename, e)
            return None
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract Tesla invoice number."""
        patterns = [
            r'Invoice\s+Number\s+([A-Z0-9]+)',
            r'Invoice\s+Number:\s*([A-Z0-9]+)',
            r'Invoice\s*#\s*([A-Z0-9]+)',
            r'Receipt\s+#\s*([A-Z0-9]+)',
            r'Transaction\s+ID[:\s]*([A-Z0-9]+)',
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
            r'Session\s+Date[:\s]*(\d{4}/\d{2}/\d{2})',  # Session Date: 2025/02/09
            r'Charging\s+Date[:\s]*(\d{4}/\d{2}/\d{2})',  # Charging Date: 2025/02/09
            r'(\d{4}/\d{2}/\d{2})',  # Standalone date in YYYY/MM/DD format
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY or DD/MM/YYYY format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    
                    # Handle different date formats
                    if re.match(r'^\d{4}/\d{1,2}/\d{1,2}, date_str):
                        # Tesla YYYY/MM/DD format
                        invoice_date = datetime.strptime(date_str, '%Y/%m/%d')
                    elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}, date_str):
                        # Try MM/DD/YYYY first (common in US)
                        try:
                            invoice_date = datetime.strptime(date_str, '%m/%d/%Y')
                        except ValueError:
                            # Try DD/MM/YYYY
                            invoice_date = datetime.strptime(date_str, '%d/%m/%Y')
                    else:
                        continue
                    
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
            r'Charging\s+Location[:\s]*([^\n]+(?:\n[^\n]+)*?)(?:\n\s*S/N:|$)',  # Location until S/N or end
            r'Supercharger\s+Location[:\s]*([^\n]+)',  # Supercharger Location: ...
            r'Location[:\s]*([^\n]+)',  # Location: ...
            r'Site[:\s]*([^\n]+)',  # Site: ...
            r'Station[:\s]*([^\n]+)',  # Station: ...
            
            # Address patterns
            r'([A-Za-z\s]+,\s*[A-Z]{2,3})\s*\n\s*([^\n]+)\s*\n\s*(\d{4}\s+[A-Za-z\s]+)',  # City, STATE \n Address \n Postcode
            r'(\d+\s+[A-Za-z\s]+(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Highway|Hwy|Lane|Ln)[^\n\r,]*,\s*[A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # Full address
            r'([A-Za-z\s]+,\s*[A-Z]{2,3}\s*\d{4})',  # City, STATE ZIP
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
            r'Amount\s+Due[:\s]*\$?([0-9]+\.[0-9]{2})',  # Amount Due: 14.93
            r'Final\s+Total[:\s]*\$?([0-9]+\.[0-9]{2})',  # Final Total: 14.93
            r'Supercharging[:\s]*\$?([0-9]+\.[0-9]{2})',  # Supercharging: 14.93
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
            r'Energy\s+Delivered[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Energy Delivered: 19.3930 kWh
            r'kWh\s+Consumed[:\s]*([0-9]+\.[0-9]+)',  # kWh Consumed: 19.3930
            r'Session\s+Energy[:\s]*([0-9]+\.[0-9]+)\s*kWh',  # Session Energy: 19.3930 kWh
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
            r'Rate[:\s]*\$?([0-9]+\.[0-9]+)\s*/?\s*kWh',  # Rate: $0.70/kWh
            r'Price[:\s]*\$?([0-9]+\.[0-9]+)\s*/?\s*kWh',  # Price: $0.70/kWh
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