import requests
import os

MOTIVE_API_KEY = os.getenv("MOTIVE_API_KEY")
BASE_URL = "https://api.gomotive.com/v1"

HEADERS = {
    "Authorization": f"Bearer {MOTIVE_API_KEY}"
}

def get_active_driver_locations():
    url = f"{BASE_URL}/fleet/drivers"
    response = requests.get(url, headers=HEADERS)
    drivers = response.json().get('data', [])

    driver_locations = []
    for driver in drivers:
        if driver.get("currentStatus") == "DRIVING" and driver.get("vehicle"):
            driver_locations.append({
                "name": driver.get("name"),
                "latitude": driver["vehicle"]["lastKnownLocation"]["latitude"],
                "longitude": driver["vehicle"]["lastKnownLocation"]["longitude"],
                "vehicle_id": driver["vehicle"]["id"]
            })
    return driver_locations
