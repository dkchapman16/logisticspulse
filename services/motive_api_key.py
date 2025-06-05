import os
import requests
from .logger import setup_logger

logger = setup_logger(__name__)

API_KEY = os.getenv("MOTIVE_API_KEY")
BASE_URL = "https://api.gomotive.com/v1"

def get_drivers():
    """Get all drivers using API key authentication"""
    if not API_KEY:
        logger.error("MOTIVE_API_KEY not found in environment")
        return []
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/drivers", headers=headers)
        logger.info(f"Drivers API response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Retrieved {len(data.get('data', []))} drivers from Motive")
            return data.get('data', [])
        else:
            logger.error(f"Failed to get drivers: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        return []

def get_vehicles():
    """Get all vehicles using API key authentication"""
    if not API_KEY:
        logger.error("MOTIVE_API_KEY not found in environment")
        return []
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/vehicles", headers=headers)
        logger.info(f"Vehicles API response: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Retrieved {len(data.get('data', []))} vehicles from Motive")
            return data.get('data', [])
        else:
            logger.error(f"Failed to get vehicles: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching vehicles: {e}")
        return []

def test_connection():
    """Test the Motive API connection and return basic info"""
    drivers = get_drivers()
    vehicles = get_vehicles()
    
    return {
        "drivers_count": len(drivers),
        "vehicles_count": len(vehicles),
        "sample_driver": drivers[0] if drivers else None,
        "sample_vehicle": vehicles[0] if vehicles else None
    }