import io
import logging
import re
from datetime import datetime
import fitz  # PyMuPDF
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)

def extract_from_pdf(file):
    """
    Extract load information from a RateCon PDF using PyMuPDF (fastest and most accurate)
    
    Args:
        file: PDF file object
    
    Returns:
        dict: Extracted load data
    """
    try:
        # Read the PDF file
        if isinstance(file, FileStorage):
            file_data = file.read()
            file.seek(0)  # Reset file pointer
        else:
            file_data = file.read()
        
        # Open PDF with PyMuPDF
        pdf_document = fitz.open(stream=file_data, filetype="pdf")
        
        full_text = ""
        # Extract text from all pages
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text = page.get_text()
            full_text += text + "\n"
        
        pdf_document.close()
        
        logger.info(f"Successfully extracted {len(full_text)} characters from PDF using PyMuPDF")
        
        # Extract load information with better patterns
        extracted_data = {
            'success': True,
            'reference_number': extract_reference_number(full_text),
            'pickup': extract_pickup_info(full_text),
            'delivery': extract_delivery_info(full_text),
            'client': extract_client_info(full_text),
            'raw_text': full_text[:1500] + "..." if len(full_text) > 1500 else full_text
        }
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting PDF data: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'reference_number': f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Pickup Location (Edit Required)',
                'address': 'Enter pickup address',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Delivery Location (Edit Required)', 
                'address': 'Enter delivery address',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Client Name (Edit Required)'
            },
            'raw_text': f'PDF extraction failed: {str(e)}'
        }

def extract_reference_number(text):
    """Extract reference/load number with improved patterns"""
    patterns = [
        r'(?i)(?:load|trip|pro|shipment|booking|order|ref(?:erence)?)\s*#?\s*[:-]?\s*([A-Z0-9-]{3,20})',
        r'(?i)rate\s*con\s*#?\s*[:-]?\s*([A-Z0-9-]{3,20})',
        r'\b([A-Z]{2,4}\d{4,8})\b',  # Pattern like ABC1234 or ABCD12345678
        r'\b(\d{6,12})\b',  # 6-12 digit numbers
        r'(?i)po\s*#?\s*[:-]?\s*([A-Z0-9-]{3,20})'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if len(match) >= 3:  # Must be at least 3 characters
                return match.strip()
    
    return f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

def extract_pickup_info(text):
    """Extract pickup information with better text analysis"""
    # Look for pickup section indicators
    pickup_keywords = ['pickup', 'origin', 'shipper', 'ship from', 'from:']
    facility_name = 'Pickup Location (Edit Required)'
    address = 'Enter pickup address'
    
    # Find pickup section
    for keyword in pickup_keywords:
        pattern = f'(?i){keyword}[:\s]*([^\n]*(?:\n[^\n]*)*?)(?=delivery|destination|consignee|ship to|to:|$)'
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            section = match.group(1).strip()
            # Extract company name (usually first non-empty line)
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            if lines:
                facility_name = lines[0][:50]  # Limit length
                # Look for address in remaining lines
                for line in lines[1:]:
                    if re.search(r'\d+.*(?:st|street|ave|avenue|rd|road|dr|drive|blvd|boulevard)', line, re.I):
                        address = line[:100]  # Limit length
                        break
            break
    
    return {
        'facility_name': facility_name,
        'address': address,
        'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def extract_delivery_info(text):
    """Extract delivery information with better text analysis"""
    # Look for delivery section indicators
    delivery_keywords = ['delivery', 'destination', 'consignee', 'ship to', 'to:']
    facility_name = 'Delivery Location (Edit Required)'
    address = 'Enter delivery address'
    
    # Find delivery section
    for keyword in delivery_keywords:
        pattern = f'(?i){keyword}[:\s]*([^\n]*(?:\n[^\n]*)*?)(?=pickup|origin|shipper|ship from|from:|$)'
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            section = match.group(1).strip()
            # Extract company name (usually first non-empty line)
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            if lines:
                facility_name = lines[0][:50]  # Limit length
                # Look for address in remaining lines
                for line in lines[1:]:
                    if re.search(r'\d+.*(?:st|street|ave|avenue|rd|road|dr|drive|blvd|boulevard)', line, re.I):
                        address = line[:100]  # Limit length
                        break
            break
    
    return {
        'facility_name': facility_name,
        'address': address,
        'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def extract_client_info(text):
    """Extract client information with improved patterns"""
    patterns = [
        r'(?i)(?:bill\s*to|customer|client|shipper)[:\s]*([A-Z][^\n]{5,50})',
        r'(?i)company[:\s]*([A-Z][^\n]{5,50})',
        r'\b([A-Z][a-zA-Z\s&]{5,40}(?:Inc|LLC|Corp|Company|Co\.|Ltd)\.?)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            client_name = match.strip()
            if len(client_name) > 5 and len(client_name) < 50:
                return {'name': client_name}
    
    return {'name': 'Client Name (Edit Required)'}