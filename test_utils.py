import unittest
import logging
from services.ocr_parser import parse_with_ai

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s'
)

def get_ai_response(prompt):
    """
    Test function for AI response validation
    """
    try:
        # Use the existing parse_with_ai function for testing
        result = parse_with_ai(prompt)
        if isinstance(result, dict):
            return str(result)
        return result
    except Exception as e:
        logging.error(f"❌ OpenAI API error: {e}")
        return "Error: AI response failed"

class TestRateParser(unittest.TestCase):
    def test_ai_response_format(self):
        response = get_ai_response("Say hello")
        self.assertIn("hello", response.lower())
    
    def test_pdf_parsing_structure(self):
        """Test that the AI parser returns expected structure"""
        sample_text = """
        Load Number: ABC123
        Pickup: XYZ Company, 123 Main St, Anytown, ST 12345
        Delivery: ABC Corp, 456 Oak Ave, Somewhere, ST 67890
        """
        result = parse_with_ai(sample_text)
        
        # Verify structure
        self.assertIn('reference_number', result)
        self.assertIn('pickup', result)
        self.assertIn('delivery', result)
        self.assertIn('client', result)
        
        # Verify nested structure
        self.assertIn('facility_name', result['pickup'])
        self.assertIn('address', result['pickup'])
        self.assertIn('facility_name', result['delivery'])
        self.assertIn('address', result['delivery'])

if __name__ == '__main__':
    unittest.main()