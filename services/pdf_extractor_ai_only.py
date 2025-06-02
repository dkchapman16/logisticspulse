import io
import logging
import os
import json
from datetime import datetime
from typing import Dict, Any
import fitz  # PyMuPDF
from werkzeug.datastructures import FileStorage
import openai

logger = logging.getLogger(__name__)

def get_openai_client():
    """Initialize OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return openai.OpenAI(api_key=api_key)

def extract_from_pdf(file) -> Dict[str, Any]:
    """
    Extract load information using PyMuPDF + AI parsing (much more reliable)
    
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
        
        logging.info("Starting OCR process")
        logger.info(f"Starting AI extraction for PDF ({len(file_data)} bytes)")
        
        # Extract text using PyMuPDF (very reliable)
        pdf_document = fitz.open(stream=file_data, filetype="pdf")
        
        full_text = ""
        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            text = page.get_text()
            full_text += f"\n--- PAGE {page_num + 1} ---\n{text}\n"
        
        pdf_document.close()
        
        logging.info(f"Extracted {len(full_text)} characters using PyMuPDF")
        logger.info(f"Extracted {len(full_text)} characters using PyMuPDF")
        
        # Use AI to intelligently parse the text
        extracted_data = parse_with_ai(full_text)
        
        # Add metadata
        extracted_data['raw_text'] = full_text[:2000] + "..." if len(full_text) > 2000 else full_text
        extracted_data['success'] = True
        
        return extracted_data
        
    except Exception as e:
        logging.error("Failed to extract text from image")
        logger.error(f"Error in PDF extraction: {str(e)}")
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
You are an expert at parsing shipping and logistics documents (Rate Confirmations/RateCons). 
Please extract the following information from this document text and return it as a JSON object.

Look carefully for:
- Load/trip/booking/order/shipment numbers (often starts with letters followed by numbers)
- Company names for pickup and delivery locations
- Addresses with street, city, state, zip
- Scheduled pickup and delivery dates/times
- Client/shipper/customer company names

Return JSON in this exact format:
{{
  "reference_number": "the load/trip/booking number found in the document",
  "pickup": {{
    "facility_name": "pickup company name",
    "address": "pickup address with city, state, zip",
    "scheduled_time": "pickup date and time in YYYY-MM-DD HH:MM:SS format if found"
  }},
  "delivery": {{
    "facility_name": "delivery company name", 
    "address": "delivery address with city, state, zip",
    "scheduled_time": "delivery date and time in YYYY-MM-DD HH:MM:SS format if found"
  }},
  "client": {{
    "name": "client/shipper/customer company name"
  }}
}}

If any information is not clearly available, use descriptive placeholders like "Edit Required - [Field Name]".

Document text:
{text}
"""

        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert at parsing shipping documents. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1000
        )
        
        # Parse the JSON response
        result = json.loads(response.choices[0].message.content)
        
        logger.info("Successfully parsed document with AI")
        return result
        
    except openai.OpenAIError as e:
        logger.error(f"❌ OpenAI API error: {e}")
        print(f"❌ OpenAI API error: {e}")
        return {
            'reference_number': f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Error: AI response failed - Edit Required',
                'address': 'Error: AI response failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Error: AI response failed - Edit Required', 
                'address': 'Error: AI response failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Error: AI response failed - Edit Required'
            }
        }
    except Exception as e:
        logger.error(f"❌ Unexpected error in AI parsing: {str(e)}")
        print(f"❌ Unexpected error in AI parsing: {str(e)}")
        return {
            'reference_number': f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Error: AI response failed - Edit Required',
                'address': 'Error: AI response failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Error: AI response failed - Edit Required', 
                'address': 'Error: AI response failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Error: AI response failed - Edit Required'
            }
        }