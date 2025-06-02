import requests
import os
from .logger import setup_logger

logger = setup_logger(__name__)

TOKEN_URL = "https://api.gomotive.com/oauth/token"
VEHICLE_LOC_URL = "https://api.gomotive.com/v3/vehicle_locations"

CLIENT_ID = os.getenv("MOTIVE_CLIENT_ID")
CLIENT_SECRET = os.getenv("MOTIVE_SECRET")

def get_access_token():
    logger.info("Getting Motive OAuth token")
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(TOKEN_URL, data=payload)
    if response.status_code != 200:
        logger.error(f"OAuth token error: {response.status_code} - {response.text}")
        return None
    return response.json().get("access_token")

def get_vehicle_locations():
    """Fetch vehicle locations using OAuth authentication"""
    token = get_access_token()
    if not token:
        return []

    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(VEHICLE_LOC_URL, headers=headers)

    logger.info(f"Response Status: {response.status_code}")
    logger.info(f"Response Body: {response.text}")

    if response.status_code != 200:
        logger.error(f"Vehicle location error: {response.status_code} - {response.text}")
        return []

    data = response.json()
    vehicles = []
    for v in data.get("data", []):
        vehicles.append({
            "vehicle_name": v.get("vehicle", {}).get("name"),
            "vehicle_id": v.get("vehicle", {}).get("id"),
            "latitude": v.get("location", {}).get("latitude"),
            "longitude": v.get("location", {}).get("longitude"),
            "driver_name": v.get("driver", {}).get("name", "Unassigned")
        })
    logger.info(f"✅ Retrieved {len(vehicles)} vehicle locations from Motive")
    return vehicles

def get_active_driver_locations():
    """Get driver data from vehicles endpoint for backward compatibility"""
    vehicles = get_vehicle_locations()
    driver_locations = []
    
    for vehicle in vehicles:
        if vehicle["driver_name"] != "Unassigned":
            driver_locations.append({
                "name": vehicle["driver_name"],
                "latitude": vehicle["latitude"],
                "longitude": vehicle["longitude"],
                "vehicle_id": vehicle["vehicle_id"]
            })
    
    return driver_locations