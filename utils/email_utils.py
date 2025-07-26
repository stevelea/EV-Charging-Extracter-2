"""Email utilities for parsing and processing with enhanced HTML support."""
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
    """Utility class for email processing with HTML support."""
    
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
    def extract_html_content(html_content: str, provider_hint: str = "") -> str:
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
            if "evie" in provider_hint.lower():
                # EVIE specific handling - look for main content areas
                main_content = soup.find(['div', 'td', 'table'], 
                                       class_=lambda x: x and any(cls in str(x).lower() 
                                                                for cls in ['content', 'main', 'body', 'receipt', 'invoice', 'email-body']))
                if main_content:
                    html_text = main_content.get_text(separator='\n', strip=True)
                else:
                    # Fallback: try to find tables or divs that might contain receipt data
                    receipt_content = soup.find_all(['table', 'div'], 
                                                  string=lambda text: text and any(keyword in text.lower() 
                                                                                  for keyword in ['receipt', 'invoice', 'total', 'amount', 'energy']))
                    if receipt_content:
                        html_text = '\n'.join([elem.get_text(separator='\n', strip=True) for elem in receipt_content])
                    else:
                        html_text = soup.get_text(separator='\n', strip=True)
            
            elif "bppulse" in provider_hint.lower() or "bp" in provider_hint.lower():
                # BP Pulse specific handling
                main_content = soup.find(['div', 'td', 'table'], 
                                       class_=lambda x: x and any(cls in str(x).lower() 
                                                                for cls in ['content', 'main', 'body', 'receipt', 'invoice']))
                if main_content:
                    html_text = main_content.get_text(separator='\n', strip=True)
                else:
                    html_text = soup.get_text(separator='\n', strip=True)
            
            else:
                # General HTML processing
                html_text = soup.get_text(separator='\n', strip=True)
            
            # Clean the extracted text
            return EmailUtils._clean_extracted_text(html_text, provider_hint)
            
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
        
        # Replace common HTML entities
        html_content = html_content.replace('&nbsp;', ' ')
        html_content = html_content.replace('&amp;', '&')
        html_content = html_content.replace('&lt;', '<')
        html_content = html_content.replace('&gt;', '>')
        html_content = html_content.replace('&quot;', '"')
        
        # Replace block-level tags with newlines
        html_content = re.sub(r'<(?:div|p|br|tr|table|h[1-6])[^>]*>', '\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</(?:div|p|tr|table|h[1-6])>', '\n', html_content, flags=re.IGNORECASE)
        
        # Remove all remaining tags
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Clean whitespace
        html_content = re.sub(r'\s+', ' ', html_content).strip()
        
        return html_content
    
    @staticmethod
    def _clean_extracted_text(text: str, provider_hint: str = "") -> str:
        """Clean extracted text based on provider."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and common email artifacts
            if not line or line in ['', ' ', '\t', '\n', '\r']:
                continue
            
            # Skip common email footer/header content
            skip_patterns = [
                'unsubscribe',
                'privacy policy',
                'terms and conditions',
                'view this email',
                'download our app',
                'follow us',
                'social media',
                'customer service',
                'help center'
            ]
            
            if any(pattern in line.lower() for pattern in skip_patterns):
                continue
            
            # Skip URLs and email addresses (unless they're part of location data)
            if (line.startswith('http') or 
                line.startswith('www.') or 
                line.startswith('mailto:') or
                '@' in line and len(line.split()) == 1):
                continue
            
            # For EVIE, be more permissive with content
            if "evie" in provider_hint.lower():
                if len(line) > 1:
                    cleaned_lines.append(line)
            else:
                # Original filtering for other providers
                if len(line) > 2:
                    cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def parse_email_content(raw_email: bytes, verbose_logging: bool = False) -> Dict[str, any]:
        """Parse email content with enhanced HTML processing and PDF extraction support."""
        try:
            msg = email.message_from_bytes(raw_email)
            
            subject = msg.get('subject', '')
            sender = msg.get('from', '')
            
            text_content = ""
            pdf_content = ""
            html_content = ""
            
            # Determine provider for specialized processing
            provider_hint = ""
            sender_lower = sender.lower()
            if "evie" in sender_lower or "goevie" in sender_lower:
                provider_hint = "evie"
            elif "bppulse" in sender_lower or "bp" in sender_lower:
                provider_hint = "bppulse"
            elif "chargefox" in sender_lower:
                provider_hint = "chargefox"
            elif "ampol" in sender_lower or "ampcharge" in sender_lower:
                provider_hint = "ampol"
            
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
            
            # Enhanced HTML processing logic
            final_text_content = text_content
            
            # If we have HTML content and either no plain text or very little plain text
            if html_content.strip():
                # Always extract from HTML for EVIE emails
                if provider_hint == "evie":
                    extracted_html = EmailUtils.extract_html_content(html_content, provider_hint)
                    if len(extracted_html) > 50:  # Reasonable threshold for EVIE
                        if verbose_logging:
                            _LOGGER.info("Using HTML content for EVIE email (extracted %d chars)", len(extracted_html))
                        final_text_content = extracted_html
                    else:
                        if verbose_logging:
                            _LOGGER.warning("HTML extraction for EVIE yielded insufficient content (%d chars)", len(extracted_html))
                
                # For other providers, fall back to HTML if plain text is insufficient
                elif len(text_content.strip()) < 100:  # Very little or no plain text
                    extracted_html = EmailUtils.extract_html_content(html_content, provider_hint)
                    minimum_threshold = 50 if provider_hint == "bppulse" else 100
                    
                    if len(extracted_html) > minimum_threshold:
                        if verbose_logging:
                            _LOGGER.info("Using HTML content for %s email (plain text: %d chars, HTML: %d chars)", 
                                       provider_hint or "unknown", len(text_content), len(extracted_html))
                        final_text_content = extracted_html
            
            # Combine final text and PDF content
            combined_content = (final_text_content + pdf_content).strip()
            
            if verbose_logging and provider_hint:
                _LOGGER.debug("Processed %s email: subject=%s, text_len=%d, html_len=%d, final_len=%d", 
                            provider_hint, subject[:50], len(text_content), len(html_content), len(combined_content))
            
            return {
                'subject': subject,
                'sender': sender,
                'text_content': combined_content,
                'has_pdf': bool(pdf_content),
                'raw_email': raw_email  # Include raw email for Tesla processing
            }
            
        except Exception as e:
            _LOGGER.error("Error parsing email: %s", e)
            return {'subject': '', 'sender': '', 'text_content': '', 'has_pdf': False}