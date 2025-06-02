import io
import logging
import os
import json
import cv2
import numpy as np
import pytesseract
from datetime import datetime
from typing import Dict, Any
import fitz  # PyMuPDF
from PIL import Image
from pdf2image import convert_from_bytes
from werkzeug.datastructures import FileStorage
import openai

logger = logging.getLogger(__name__)

def get_openai_client():
    """Initialize OpenAI client"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return openai.OpenAI(api_key=api_key)

def preprocess_and_ocr(image):
    """
    Apply OpenCV preprocessing to clean up the image before OCR
    
    Args:
        image: PIL Image or numpy array
    
    Returns:
        str: Extracted text from the preprocessed image
    """
    try:
        logging.info("Starting OCR process with OpenCV preprocessing")
        
        # Convert PIL Image to numpy array if needed
        if isinstance(image, Image.Image):
            img_array = np.array(image)
        else:
            img_array = image
            
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
            
        # Apply preprocessing techniques
        # 1. Noise reduction
        denoised = cv2.medianBlur(gray, 3)
        
        # 2. Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 3. Thresholding to create binary image
        cleaned = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY)[1]
        
        # 4. Morphological operations to clean up
        kernel = np.ones((1,1), np.uint8)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)
        
        # Extract text using Tesseract
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-/() '
        text = pytesseract.image_to_string(cleaned, config=custom_config)
        
        logging.info(f"OCR extracted {len(text)} characters from preprocessed image")
        return text.strip()
        
    except Exception as e:
        logging.error(f"Failed to extract text from image: {str(e)}")
        logger.error(f"Error in OCR preprocessing: {str(e)}")
        return ""

def extract_from_pdf_with_ocr(file) -> Dict[str, Any]:
    """
    Extract load information using multi-stage approach: PyMuPDF + OCR + AI parsing
    
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
        logger.info(f"Starting multi-stage extraction for PDF ({len(file_data)} bytes)")
        
        # Stage 1: Try PyMuPDF text extraction first (fastest)
        full_text = ""
        try:
            pdf_document = fitz.open(stream=file_data, filetype="pdf")
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text = page.get_text()
                full_text += f"\n--- PAGE {page_num + 1} ---\n{text}\n"
            
            pdf_document.close()
            logging.info(f"PyMuPDF extracted {len(full_text)} characters")
            
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {str(e)}")
            full_text = ""
        
        # Stage 2: If PyMuPDF didn't get enough text, use OCR
        if len(full_text.strip()) < 100:  # If very little text extracted
            logging.info("Low text yield from PyMuPDF, falling back to OCR")
            
            try:
                # Convert PDF pages to images
                images = convert_from_bytes(file_data, dpi=300)
                
                ocr_text = ""
                for page_num, image in enumerate(images):
                    logging.info(f"Processing page {page_num + 1} with OCR")
                    page_text = preprocess_and_ocr(image)
                    ocr_text += f"\n--- PAGE {page_num + 1} (OCR) ---\n{page_text}\n"
                
                # Combine or replace text based on quality
                if len(ocr_text.strip()) > len(full_text.strip()):
                    full_text = ocr_text
                    logging.info(f"OCR provided better results: {len(ocr_text)} characters")
                else:
                    full_text += f"\n--- OCR SUPPLEMENT ---\n{ocr_text}"
                    
            except Exception as e:
                logging.error(f"OCR fallback failed: {str(e)}")
                logger.error(f"OCR processing error: {str(e)}")
        
        # Stage 3: Use AI to intelligently parse the text
        extracted_data = parse_with_ai(full_text)
        
        # Add metadata
        extracted_data['raw_text'] = full_text[:2000] + "..." if len(full_text) > 2000 else full_text
        extracted_data['success'] = True
        extracted_data['extraction_method'] = 'multi-stage'
        
        return extracted_data
        
    except Exception as e:
        logging.error("Failed to extract text from image")
        logger.error(f"Error in PDF extraction: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'reference_number': f"LOAD-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Error: Extraction failed - Edit Required',
                'address': 'Error: Extraction failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Error: Extraction failed - Edit Required', 
                'address': 'Error: Extraction failed - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Error: Extraction failed - Edit Required'
            },
            'raw_text': f'PDF extraction failed: {str(e)}',
            'extraction_method': 'failed'
        }

def parse_with_ai(text: str) -> Dict[str, Any]:
    """
    Use OpenAI GPT to intelligently parse RateCon text data
    """
    # Check for Safe Mode
    from flask import current_app
    if current_app and current_app.config.get("SAFE_MODE", False):
        logging.info("Safe mode enabled – no API calls will be made")
        return {
            'reference_number': f"SAFE-MODE-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            'pickup': {
                'facility_name': 'Safe Mode - Edit Required',
                'address': 'Safe Mode - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'delivery': {
                'facility_name': 'Safe Mode - Edit Required', 
                'address': 'Safe Mode - Edit Required',
                'scheduled_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'client': {
                'name': 'Safe Mode - Edit Required'
            }
        }
    
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
        logging.error(f"OpenAI API error: {e}")
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
        logging.error(f"Unexpected error in AI parsing: {str(e)}")
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