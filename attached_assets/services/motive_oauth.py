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

    d_resp = requests.get("https://api.gomotive.com/v1/fleet/drivers", headers=headers)
    if d_resp.status_code == 200:
        drivers = [d["name"] for d in d_resp.json().get("data", []) if d.get("name")]

    v_resp = requests.get("https://api.gomotive.com/v1/fleet/vehicles", headers=headers)
    if v_resp.status_code == 200:
        vehicles = [v["name"] for v in v_resp.json().get("data", []) if v.get("name")]

    return drivers, vehicles
