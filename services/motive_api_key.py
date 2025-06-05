import os
import requests
from .logger import setup_logger

logger = setup_logger(__name__)

API_KEY = os.getenv("MOTIVE_API_KEY")
BASE_URL = "https://api.gomotive.com/v1"

def get_drivers():
    """Get all drivers using API key authentication with pagination"""
    if not API_KEY:
        logger.error("MOTIVE_API_KEY not found in environment")
        return []
    
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Use the working users endpoint with pagination
    endpoint = "https://api.gomotive.com/v1/users"
    all_drivers = []
    page = 1
    
    try:
        while True:
            response = requests.get(f"{endpoint}?page_no={page}", headers=headers)
            logger.info(f"Drivers API ({endpoint}) page {page} response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                drivers = data.get('users', [])
                all_drivers.extend(drivers)
                
                # Check pagination
                pagination = data.get('pagination', {})
                total_pages = (pagination.get('total', 0) + pagination.get('per_page', 25) - 1) // pagination.get('per_page', 25)
                
                if page >= total_pages:
                    break
                page += 1
            else:
                logger.error(f"Failed to get drivers page {page}: {response.status_code} - {response.text}")
                break
        
        # Filter for only active drivers (role=driver, status=active)
        active_drivers = []
        for user_item in all_drivers:
            user_data = user_item.get('user', {})
            if user_data.get('status') == 'active' and user_data.get('role') == 'driver':
                active_drivers.append(user_item)
        
        logger.info(f"Retrieved {len(all_drivers)} total users, {len(active_drivers)} active drivers from Motive across {page} pages")
        return active_drivers
    except Exception as e:
        logger.error(f"Error getting drivers: {e}")
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