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
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Try multiple potential endpoints
    endpoints = [
        f"{BASE_URL}/drivers",
        f"{BASE_URL}/users",
        "https://api.gomotive.com/v1/drivers",
        "https://api.gomotive.com/v2/drivers",
        "https://api.gomotive.com/drivers"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers)
            logger.info(f"Drivers API ({endpoint}) response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                drivers = data.get('data', data.get('drivers', data.get('users', [])))
                if drivers:
                    logger.info(f"Retrieved {len(drivers)} drivers from Motive")
                    return drivers
            elif response.status_code != 404:
                logger.info(f"Response from {endpoint}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error with endpoint {endpoint}: {e}")
            continue
    
    return []

def get_vehicles():
    """Get all vehicles using API key authentication"""
    if not API_KEY:
        logger.error("MOTIVE_API_KEY not found in environment")
        return []
    
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Try multiple potential endpoints
    endpoints = [
        f"{BASE_URL}/vehicles",
        f"{BASE_URL}/assets",
        "https://api.gomotive.com/v1/vehicles", 
        "https://api.gomotive.com/v2/vehicles",
        "https://api.gomotive.com/vehicles"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(endpoint, headers=headers)
            logger.info(f"Vehicles API ({endpoint}) response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                vehicles = data.get('data', data.get('vehicles', data.get('assets', [])))
                if vehicles:
                    logger.info(f"Retrieved {len(vehicles)} vehicles from Motive")
                    return vehicles
                else:
                    logger.info(f"Empty response from {endpoint}: {data}")
            elif response.status_code != 404:
                logger.info(f"Response from {endpoint}: {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error with endpoint {endpoint}: {e}")
            continue
    
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