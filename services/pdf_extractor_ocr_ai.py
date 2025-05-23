import io
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image
from werkzeug.datastructures import FileStorage
import openai

# Configure tesseract path for Replit environment
import subprocess
try:
    tesseract_path = subprocess.check_output(['which', 'tesseract']).decode().strip()
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
except:
    # Fallback path
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

logger = logging.getLogger(__name__)

# Initialize OpenAI client
def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return openai.OpenAI(api_key=api_key)

def extract_from_pdf(file) -> Dict[str, Any]:
    """
    Extract load information from a RateCon PDF using OCR + AI parsing
    
    Args:
        file: PDF file object
    
    Returns:
        dict: Extracted load data
    """
    try:
        # Read the PDF file
        if isinstance(file, FileStorage):
            pdf_bytes = file.read()
            file.seek(0)  # Reset file pointer
        else:
            pdf_bytes = file.read()
        
        logger.info(f"Starting OCR + AI extraction for PDF ({len(pdf_bytes)} bytes)")
        
        # Step 1: Convert PDF pages to images
        # Specify poppler path for Replit environment
        poppler_path = "/nix/store/1f2vbia1rg1rh5cs0ii49v3hln9i36rv-poppler-utils-24.02.0/bin"
        images = convert_from_bytes(pdf_bytes, dpi=300, fmt='PNG', poppler_path=poppler_path)
        logger.info(f"Converted PDF to {len(images)} images")
        
        # Step 2: Extract text using OCR from all pages
        full_text = ""
        for i, image in enumerate(images):
            # Use pytesseract for OCR
            page_text = pytesseract.image_to_string(image, lang='eng')
            full_text += f"\n--- PAGE {i+1} ---\n{page_text}\n"
        
        logger.info(f"OCR extracted {len(full_text)} characters from PDF")
        
        # Step 3: Use OpenAI to parse the extracted text
        extracted_data = parse_with_ai(full_text)
        
        # Add raw text for debugging
        extracted_data['raw_text'] = full_text[:1500] + "..." if len(full_text) > 1500 else full_text
        extracted_data['success'] = True
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"Error in OCR + AI extraction: {str(e)}")
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

def parse_with_ai(text: str) -> Dict[str, Any]:
    """
    Use OpenAI GPT to intelligently parse RateCon text data
    """
    try:
        client = get_openai_client()
        
        prompt = f"""
You are an expert at parsing shipping and logistics documents (RateConfirmations/RateCons). 
Please extract the following information from this document text and return it as a JSON object:

{{
  "reference_number": "load/trip/booking/order/shipment number",
  "pickup": {{
    "facility_name": "pickup company/facility name",
    "address": "pickup address with city, state, zip",
    "scheduled_time": "pickup date and time in YYYY-MM-DD HH:MM:SS format"
  }},
  "delivery": {{
    "facility_name": "delivery company/facility name", 
    "address": "delivery address with city, state, zip",
    "scheduled_time": "delivery date and time in YYYY-MM-DD HH:MM:SS format"
  }},
  "client": {{
    "name": "client/shipper/customer company name"
  }}
}}

If any information is not clearly available, use descriptive placeholders like "Edit Required - Pickup Location".

Document text:
{text}
"""

        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at parsing shipping documents. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for consistent parsing
        )
        
        # Parse the JSON response
        import json
        result = json.loads(response.choices[0].message.content)
        
        logger.info("Successfully parsed document with AI")
        return result
        
    except Exception as e:
        logger.error(f"Error in AI parsing: {str(e)}")
        # Fallback to basic parsing if AI fails
        return {
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
            }
        }