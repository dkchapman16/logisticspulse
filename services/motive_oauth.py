import os
import requests
from .logger import setup_logger

logger = setup_logger(__name__)

TOKEN_URL = "https://api.gomotive.com/oauth/token"
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

def get_driver_vehicle_list():
    token = get_access_token()
    if not token:
        return [], []

    headers = {"Authorization": f"Bearer {token}"}
    drivers, vehicles = [], []

    # Try to get drivers from the correct endpoint
    try:
        d_resp = requests.get("https://api.gomotive.com/v1/drivers", headers=headers)
        if d_resp.status_code == 200:
            data = d_resp.json()
            drivers = [d.get("name", d.get("first_name", "") + " " + d.get("last_name", "")).strip() 
                      for d in data.get("drivers", data.get("data", [])) 
                      if d.get("name") or (d.get("first_name") or d.get("last_name"))]
        else:
            logger.warning(f"Drivers endpoint returned {d_resp.status_code}: {d_resp.text}")
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")

    # Try to get vehicles from the correct endpoint
    try:
        v_resp = requests.get("https://api.gomotive.com/v1/vehicles", headers=headers)
        if v_resp.status_code == 200:
            data = v_resp.json()
            vehicles = [v.get("number", v.get("license_plate", v.get("id", "Unknown"))) 
                       for v in data.get("vehicles", data.get("data", [])) 
                       if v.get("number") or v.get("license_plate") or v.get("id")]
        else:
            logger.warning(f"Vehicles endpoint returned {v_resp.status_code}: {v_resp.text}")
    except Exception as e:
        logger.error(f"Error fetching vehicles: {e}")

    return drivers, vehicles