import requests
import os
from .logger import setup_logger

logger = setup_logger(__name__)

MOTIVE_API_KEY = os.getenv("MOTIVE_API_KEY")
BASE_URL = "https://api.gomotive.com/v1"

HEADERS = {
    "Authorization": f"Bearer {MOTIVE_API_KEY}"
}

def get_active_driver_locations():
    """Get all drivers and extract real-time location if available"""
    logger.info("Fetching drivers from Motive")
    url = f"{BASE_URL}/fleet/drivers"
    driver_locations = []
    cursor = None

    while True:
        params = {"limit": 50}
        if cursor:
            params["starting_after"] = cursor

        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            logger.error(f"Motive API Error: {response.status_code} - {response.text}")
            break

        data = response.json()
        drivers = data.get("data", [])

        for driver in drivers:
            vehicle = driver.get("vehicle")
            if vehicle and vehicle.get("lastKnownLocation"):
                driver_locations.append({
                    "name": driver.get("name"),
                    "latitude": vehicle["lastKnownLocation"]["latitude"],
                    "longitude": vehicle["lastKnownLocation"]["longitude"],
                    "vehicle_id": vehicle["id"]
                })

        cursor = data.get("pagination", {}).get("ending_before")
        if not cursor:
            break

    logger.info(f"✅ Found {len(driver_locations)} drivers with live location")
    return driver_locations