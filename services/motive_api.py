import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# API Configuration
MOTIVE_API_BASE_URL = "https://api.gomotive.com/v1"
MOTIVE_API_KEY = os.environ.get("MOTIVE_API_KEY", "")

def get_headers():
    """Get the headers needed for Motive API requests"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MOTIVE_API_KEY}"
    }

def get_driver_location(driver_id):
    """
    Get the current location of a driver using the Motive API
    
    Args:
        driver_id (str): The Motive driver ID
    
    Returns:
        dict: Location data including lat, lng, speed, and timestamp
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return None
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/drivers/{driver_id}/location"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract the relevant location data
            location = {
                "lat": data.get("latitude"),
                "lng": data.get("longitude"),
                "speed": data.get("speed_mph"),
                "heading": data.get("heading"),
                "timestamp": datetime.utcnow(),  # Use current time as API response may not include timestamp
                "status": data.get("status", "unknown")
            }
            
            return location
        else:
            logger.error(f"Error getting driver location: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_driver_location: {str(e)}")
        return None

def get_vehicle_location(vehicle_id):
    """
    Get the current location of a vehicle using the Motive API
    
    Args:
        vehicle_id (str): The Motive vehicle ID
    
    Returns:
        dict: Location data including lat, lng, speed, and timestamp
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return None
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/vehicles/{vehicle_id}/location"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract the relevant location data
            location = {
                "lat": data.get("latitude"),
                "lng": data.get("longitude"),
                "speed": data.get("speed_mph"),
                "heading": data.get("heading"),
                "timestamp": datetime.utcnow(),
                "status": data.get("status", "unknown")
            }
            
            return location
        else:
            logger.error(f"Error getting vehicle location: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_vehicle_location: {str(e)}")
        return None

def get_driver_info(driver_id):
    """
    Get information about a driver using the Motive API
    
    Args:
        driver_id (str): The Motive driver ID
    
    Returns:
        dict: Driver data
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return None
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/drivers/{driver_id}"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting driver info: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_driver_info: {str(e)}")
        return None

def get_vehicle_info(vehicle_id):
    """
    Get information about a vehicle using the Motive API
    
    Args:
        vehicle_id (str): The Motive vehicle ID
    
    Returns:
        dict: Vehicle data
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return None
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/vehicles/{vehicle_id}"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error getting vehicle info: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_vehicle_info: {str(e)}")
        return None

def list_drivers(page=1, limit=100):
    """
    List all drivers in the Motive account
    
    Args:
        page (int): Page number for pagination
        limit (int): Number of results per page
    
    Returns:
        list: List of driver data
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return []
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/drivers?page={page}&per_page={limit}"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            return response.json().get("drivers", [])
        else:
            logger.error(f"Error listing drivers: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Exception in list_drivers: {str(e)}")
        return []

def list_vehicles(page=1, limit=100):
    """
    List all vehicles in the Motive account
    
    Args:
        page (int): Page number for pagination
        limit (int): Number of results per page
    
    Returns:
        list: List of vehicle data
    """
    if not MOTIVE_API_KEY:
        logger.error("Motive API key not configured")
        return []
    
    try:
        url = f"{MOTIVE_API_BASE_URL}/vehicles?page={page}&per_page={limit}"
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            return response.json().get("vehicles", [])
        else:
            logger.error(f"Error listing vehicles: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Exception in list_vehicles: {str(e)}")
        return []
