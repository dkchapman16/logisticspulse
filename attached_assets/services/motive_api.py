import requests
import os
from .logger import setup_logger

logger = setup_logger(__name__)

MOTIVE_API_KEY = os.getenv("MOTIVE_API_KEY")
BASE_URL = "https://api.gomotive.com/v1"

HEADERS = {
    "Authorization": f"Bearer {MOTIVE_API_KEY}"
}

def get_vehicle_locations():
    """Fetch vehicle locations and assigned drivers using Motive's /fleet/vehicles endpoint"""
    logger.info(f"MOTIVE_API_KEY set: {'Yes' if MOTIVE_API_KEY else 'No'}")
    logger.info("Fetching vehicle data from Motive")

    url = f"{BASE_URL}/fleet/vehicles"
    vehicles = []
    cursor = None

    while True:
        params = {"limit": 50}
        if cursor:
            params["starting_after"] = cursor

        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            logger.error(f"Motive API Error: {response.status_code} - {response.text}")
            return []

        data = response.json()
        for v in data.get("data", []):
            location = v.get("lastKnownLocation")
            if location:
                vehicles.append({
                    "vehicle_name": v.get("name"),
                    "vehicle_id": v.get("id"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "driver_name": v.get("driver", {}).get("name", "Unassigned")
                })

        cursor = data.get("pagination", {}).get("ending_before")
        if not cursor:
            break

    logger.info(f"✅ Found {len(vehicles)} vehicles with location data")
    return vehicles
