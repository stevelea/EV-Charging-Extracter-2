"""Processor modules for EV charging data."""

from .database_manager import DatabaseManager
from .email_processor import EmailProcessor
from .evcc_processor import EVCCProcessor

try:
    from .tesla_pdf_processor import TeslaPDFProcessor
    __all__ = ['DatabaseManager', 'EmailProcessor', 'EVCCProcessor', 'TeslaPDFProcessor']
except ImportError:
    # Tesla processor not available (missing PyPDF2 or file not created yet)
    __all__ = ['DatabaseManager', 'EmailProcessor', 'EVCCProcessor']