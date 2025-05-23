import io
import logging
import re
from datetime import datetime
import pdfplumber
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

def extract_from_pdf(file):
    """
    Extract load information from a RateCon PDF using pdfplumber
    
    Args:
        file: PDF file object
    
    Returns:
        dict: Extracted load data
    """
    try:
        # Read the PDF file
        if isinstance(file, FileStorage):
            file_stream = io.BytesIO(file.read())
            file.seek(0)  # Reset file pointer
        else:
            file_stream = file
        
        # Parse PDF content with pdfplumber
        with pdfplumber.open(file_stream) as pdf:
            full_text = ""
            
            # Extract text from all pages
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
        
        logger.info(f"Extracted {len(full_text)} characters from PDF")
        
        # Extract load information
        extracted_data = {
            'reference_number': extract_reference_number(full_text),
            'pickup': extract_pickup_info(full_text),
            'delivery': extract_delivery_info(full_text),
            'client': extract_client_info(full_text),
            'raw_text': full_text[:1000] + "..." if len(full_text) > 1000 else full_text
        }
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting PDF data: {str(e)}")
        return {
            'error': str(e),
            'reference_number': f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Pickup Location (Please Edit)',
                'address': 'Enter pickup address',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Delivery Location (Please Edit)', 
                'address': 'Enter delivery address',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Client Name (Please Edit)'
            },
            'raw_text': f'PDF extraction failed: {str(e)}'
        }

def extract_reference_number(text):
    """Extract reference/load number from text"""
    # Try different patterns for reference numbers
    patterns = [
        r'(?i)load\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)load\s*number\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)reference\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)trip\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)booking\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)order\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)shipment\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'(?i)pro\s*#?\s*[:-]?\s*([A-Z0-9-]+)',
        r'([A-Z]{2,}\d{4,})',  # Pattern like ABC1234
        r'(\d{6,})',  # 6+ digit numbers
        r'(?i)PO\s*#?\s*[:-]?\s*(\w+)',
        r'(?i)Rate\s*Con\s*#?\s*[:-]?\s*(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def extract_pickup_info(text):
    """Extract pickup information from text"""
    # Look for pickup patterns
    patterns = [
        r'(?i)pickup.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)origin.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)shipper.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)'
    ]
    
    facility_name = 'Pickup Location (Please Edit)'
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            facility_name = match.group(1).strip()
            break
    
    return {
        'facility_name': facility_name,
        'address': 'Enter pickup address',
        'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def extract_delivery_info(text):
    """Extract delivery information from text"""
    # Look for delivery patterns
    patterns = [
        r'(?i)delivery.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)destination.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)consignee.*?([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)'
    ]
    
    facility_name = 'Delivery Location (Please Edit)'
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            facility_name = match.group(1).strip()
            break
    
    return {
        'facility_name': facility_name,
        'address': 'Enter delivery address',
        'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def extract_client_info(text):
    """Extract client information from text"""
    # Try to find client/shipper names
    patterns = [
        r'(?i)shipper\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)client\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)',
        r'(?i)customer\s*:?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            client_name = match.group(1).strip()
            if len(client_name) > 2:
                return {'name': client_name}
    
    return {'name': 'Client Name (Please Edit)'}