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
    # Look for customer/client section
    client_section = extract_section(text, 'customer', None) or extract_section(text, 'client', None)
    
    if not client_section:
        client_section = text
    
    # Try to extract client name
    client_patterns = [
        r'Customer\s*[:-]?\s*([\w\s]+)',
        r'Client\s*[:-]?\s*([\w\s]+)',
        r'Shipper\s*[:-]?\s*([\w\s]+)',
        r'Company\s*[:-]?\s*([\w\s]+)'
    ]
    
    for pattern in client_patterns:
        match = re.search(pattern, client_section, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no match found, return empty string
    return ""

def extract_section(text, start_keyword, end_keyword):
    """Extract a section of text between start and end keywords"""
    # Compile patterns for the start and end sections
    start_pattern = re.compile(r'\b' + start_keyword + r'\b', re.IGNORECASE)
    
    # Find the start position
    start_match = start_pattern.search(text)
    if not start_match:
        return None
    
    start_pos = start_match.end()
    
    # Find the end position if end_keyword is provided
    if end_keyword:
        end_pattern = re.compile(r'\b' + end_keyword + r'\b', re.IGNORECASE)
        end_match = end_pattern.search(text[start_pos:])
        
        if end_match:
            end_pos = start_pos + end_match.start()
            return text[start_pos:end_pos]
    
    # If no end keyword or no match, return to the end of the text
    return text[start_pos:]

def extract_address(text):
    """Extract address from text"""
    # Look for address patterns
    address_patterns = [
        r'Address\s*[:-]?\s*([\w\s,.#-]+)',
        r'Location\s*[:-]?\s*([\w\s,.#-]+)',
        r'Street\s*[:-]?\s*([\w\s,.#-]+)',
        # This pattern looks for a structure of a typical address: street number + name + city/state/zip
        r'\b(\d+\s+[\w\s,.#-]+\b(?:Avenue|Ave|Boulevard|Blvd|Circle|Cir|Court|Ct|Drive|Dr|Lane|Ln|Parkway|Pkwy|Place|Pl|Plaza|Plz|Road|Rd|Square|Sq|Street|St|Way)[\w\s,.#-]+\d{5}(?:-\d{4})?)\b'
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no match, try a more general approach to find address-like lines
    lines = text.split('\n')
    for line in lines:
        if re.search(r'\d+\s+[\w\s]+,\s*\w+,\s*\w{2}\s*\d{5}', line, re.IGNORECASE):
            return line.strip()
    
    # If no match found, return empty string
    return ""

def extract_date_time(text):
    """Extract date and time from text"""
    # Look for date and time patterns
    date_time_patterns = [
        # MM/DD/YYYY HH:MM AM/PM
        r'(\d{1,2}/\d{1,2}/\d{2,4})\s*(?:@|at)?\s*(\d{1,2}:\d{2}\s*(?:AM|PM)?)',
        # Month name, day, year
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{2,4}\s+\d{1,2}:\d{2}\s*(?:AM|PM)?',
        # YYYY-MM-DD HH:MM
        r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})',
        # Just date patterns
        r'(\d{1,2}/\d{1,2}/\d{2,4})',
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{2,4}',
        r'(\d{4}-\d{2}-\d{2})'
    ]
    
    for pattern in date_time_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            try:
                # Try various datetime formats
                formats = [
                    '%m/%d/%Y %I:%M %p',
                    '%m/%d/%Y %I:%M%p',
                    '%m/%d/%Y %H:%M',
                    '%m/%d/%y %I:%M %p',
                    '%m/%d/%y %I:%M%p',
                    '%m/%d/%y %H:%M',
                    '%B %d, %Y %I:%M %p',
                    '%B %d, %Y %I:%M%p',
                    '%B %d, %Y %H:%M',
                    '%b %d, %Y %I:%M %p',
                    '%b %d, %Y %I:%M%p',
                    '%b %d, %Y %H:%M',
                    '%Y-%m-%d %H:%M',
                    '%m/%d/%Y',
                    '%m/%d/%y',
                    '%B %d, %Y',
                    '%B %d %Y',
                    '%b %d, %Y',
                    '%b %d %Y',
                    '%Y-%m-%d'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        # Return in ISO format
                        return dt.isoformat()
                    except ValueError:
                        continue
                
                # If no format worked, return the raw string
                return date_str
                
            except Exception:
                return date_str
    
    # If no match found, return empty string
    return ""
