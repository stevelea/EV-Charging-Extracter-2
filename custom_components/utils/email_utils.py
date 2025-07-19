"""Email utilities for parsing and processing."""
import email
import logging
from typing import Dict, Optional

try:
    from bs4 import BeautifulSoup
    import PyPDF2
    import io
except ImportError:
    BeautifulSoup = None
    PyPDF2 = None
    io = None

_LOGGER = logging.getLogger(__name__)


class EmailUtils:
    """Utility class for email processing."""
    
    @staticmethod
    def extract_pdf_text(pdf_data: bytes) -> str:
        """Extract text from PDF attachment."""
        try:
            if not PyPDF2:
                _LOGGER.warning("PyPDF2 not available, cannot process PDF attachments")
                return ""
            
            pdf_file = io.BytesIO(pdf_data)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    _LOGGER.warning("Error extracting text from PDF page: %s", e)
                    continue
            
            return text
        except Exception as e:
            _LOGGER.error("Error processing PDF: %s", e)
            return ""
    
    @staticmethod
    def extract_html_content(html_content: str, is_evie: bool = False, is_bp_pulse: bool = False) -> str:
        """Extract text content from HTML with provider-specific handling."""
        if not BeautifulSoup:
            _LOGGER.warning("BeautifulSoup not available, using simple HTML stripping")
            return EmailUtils._simple_html_strip(html_content)
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Provider-specific content extraction
            if is_bp_pulse:
                # Look for common BP Pulse content containers
                main_content = soup.find(['div', 'td', 'table'], 
                                       class_=lambda x: x and any(cls in str(x).lower() 
                                                                for cls in ['content', 'main', 'body', 'receipt', 'invoice']))
                if main_content:
                    html_text = main_content.get_text(separator='\n', strip=True)
                else:
                    html_text = soup.get_text(separator='\n', strip=True)
            else:
                html_text = soup.get_text(separator='\n', strip=True)
            
            # Clean the extracted text
            return EmailUtils._clean_extracted_text(html_text, is_bp_pulse)
            
        except Exception as e:
            _LOGGER.error("Error extracting HTML content: %s", e)
            return EmailUtils._simple_html_strip(html_content)
    
    @staticmethod
    def _simple_html_strip(html_content: str) -> str:
        """Simple HTML stripping fallback."""
        import re
        
        # Remove scripts and styles
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace tags with newlines
        html_content = re.sub(r'<[^>]+>', '\n', html_content)
        
        # Clean whitespace
        html_content = re.sub(r'\s+', ' ', html_content).strip()
        
        return html_content
    
    @staticmethod
    def _clean_extracted_text(text: str, is_bp_pulse: bool = False) -> str:
        """Clean extracted text based on provider."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            if is_bp_pulse:
                # For BP Pulse, be very permissive - only remove obvious junk
                if line and line not in ['', ' ', '\t', '\n', '\r']:
                    cleaned_lines.append(line)
            else:
                # Original EVIE logic
                if (line and 
                    len(line) > 1 and
                    not line.startswith('http') and
                    not line.startswith('www.') and
                    not line.startswith('mailto:') and
                    line not in ['', ' ', '\t', '\n']):
                    cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def parse_email_content(raw_email: bytes, verbose_logging: bool = False) -> Dict[str, any]:
        """Parse email content with HTML extraction support."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            subject = msg.get('subject', '')
            sender = msg.get('from', '')
            
            text_content = ""
            pdf_content = ""
            html_content = ""
            
            # Parse email parts
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    # Handle PDF attachments
                    if content_type == "application/pdf":
                        filename = part.get_filename()
                        if filename:
                            try:
                                pdf_data = part.get_payload(decode=True)
                                if pdf_data:
                                    pdf_text = EmailUtils.extract_pdf_text(pdf_data)
                                    if pdf_text:
                                        pdf_content += f"\n=== PDF: {filename} ===\n{pdf_text}\n"
                            except Exception as e:
                                _LOGGER.warning("Error processing PDF attachment %s: %s", filename, e)
                    
                    # Handle text content
                    elif content_type == "text/plain":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                decoded_text = payload.decode('utf-8', errors='ignore')
                                if decoded_text.strip():
                                    text_content += decoded_text + "\n"
                        except Exception as e:
                            if verbose_logging:
                                _LOGGER.debug("Error decoding text/plain: %s", e)
                    
                    # Handle HTML content
                    elif content_type == "text/html":
                        try:
                            payload = part.get_payload(decode=True)
                            if payload:
                                html_text = payload.decode('utf-8', errors='ignore')
                                if html_text.strip():
                                    html_content += html_text + "\n"
                        except Exception as e:
                            if verbose_logging:
                                _LOGGER.debug("Error decoding text/html: %s", e)
            else:
                # Handle non-multipart messages
                payload = msg.get_payload(decode=True)
                if payload:
                    try:
                        decoded_text = payload.decode('utf-8', errors='ignore')
                        if decoded_text.strip():
                            text_content = decoded_text
                    except Exception as e:
                        if verbose_logging:
                            _LOGGER.debug("Error decoding non-multipart content: %s", e)
            
            # Check if this needs HTML extraction
            is_evie_email = "goevie.com.au" in sender.lower()
            is_bp_pulse = "bppulse.com.au" in sender.lower()
            
            # Force HTML extraction for certain providers if plain text is insufficient
            if (is_evie_email or is_bp_pulse) and html_content.strip() and len(text_content.strip()) < 1000:
                extracted_text = EmailUtils.extract_html_content(html_content, is_evie_email, is_bp_pulse)
                
                minimum_threshold = 50 if is_bp_pulse else 100
                if len(extracted_text) > minimum_threshold:
                    text_content = extracted_text
            
            # Combine text and PDF content
            combined_content = (text_content + pdf_content).strip()
            
            return {
                'subject': subject,
                'sender': sender,
                'text_content': combined_content,
                'has_pdf': bool(pdf_content)
            }
            
        except Exception as e:
            _LOGGER.error("Error parsing email: %s", e)
            return {'subject': '', 'sender': '', 'text_content': '', 'has_pdf': False}
