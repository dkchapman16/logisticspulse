import io
import logging
import re
from datetime import datetime
import PyPDF2
from werkzeug.datastructures import FileStorage
from services.google_maps_api import get_geocode

logger = logging.getLogger(__name__)

def extract_from_pdf(file):
    """
    Extract load information from a RateCon PDF
    
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
        
        # Parse PDF content
        pdf_reader = PyPDF2.PdfReader(file_stream)
        text = ""
        
        # Extract text from all pages
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        
        # Extract load information
        extracted_data = {
            'reference_number': extract_reference_number(text),
            'pickup': extract_pickup_info(text),
            'delivery': extract_delivery_info(text),
            'client': extract_client_info(text)
        }
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error extracting PDF data: {str(e)}")
        return {
            'error': str(e),
            'partial_data': {}
        }

def extract_reference_number(text):
    """Extract reference/load number from text"""
    # Try different patterns for reference numbers
    patterns = [
        r'Load\s*#?\s*[:-]?\s*(\w+)',
        r'Load\s*Number\s*[:-]?\s*(\w+)',
        r'Reference\s*#?\s*[:-]?\s*(\w+)',
        r'Trip\s*#?\s*[:-]?\s*(\w+)',
        r'Booking\s*#?\s*[:-]?\s*(\w+)',
        r'Order\s*#?\s*[:-]?\s*(\w+)',
        r'PO\s*#?\s*[:-]?\s*(\w+)',
        r'Rate\s*Con\s*#?\s*[:-]?\s*(\w+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # If no match found, return empty string
    return ""

def extract_pickup_info(text):
    """Extract pickup information from text"""
    # Try to find pickup section
    pickup_section = extract_section(text, 'pickup', 'delivery')
    
    if not pickup_section:
        # Try alternative section names
        pickup_section = extract_section(text, 'origin', 'destination')
    
    if not pickup_section:
        # If no clear section, use the whole text
        pickup_section = text
    
    # Extract address
    address = extract_address(pickup_section)
    
    # Extract date and time
    date_time = extract_date_time(pickup_section)
    
    # Get coordinates from address if found
    coordinates = None
    if address:
        geocode_result = get_geocode(address)
        if geocode_result:
            coordinates = {
                'lat': geocode_result['lat'],
                'lng': geocode_result['lng']
            }
    
    return {
        'address': address,
        'date_time': date_time,
        'coordinates': coordinates
    }

def extract_delivery_info(text):
    """Extract delivery information from text"""
    # Try to find delivery section
    delivery_section = extract_section(text, 'delivery', None)
    
    if not delivery_section:
        # Try alternative section names
        delivery_section = extract_section(text, 'destination', None)
    
    if not delivery_section:
        # If no clear section, use the whole text
        delivery_section = text
    
    # Extract address
    address = extract_address(delivery_section)
    
    # Extract date and time
    date_time = extract_date_time(delivery_section)
    
    # Get coordinates from address if found
    coordinates = None
    if address:
        geocode_result = get_geocode(address)
        if geocode_result:
            coordinates = {
                'lat': geocode_result['lat'],
                'lng': geocode_result['lng']
            }
    
    return {
        'address': address,
        'date_time': date_time,
        'coordinates': coordinates
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
