import requests
import os
from .logger import setup_logger

logger = setup_logger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

def get_eta(origin_lat, origin_lng, dest_address):
    """Calculate ETA from origin coordinates to destination address"""
    logger.info(f"Calculating ETA from {origin_lat},{origin_lng} to {dest_address}")
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": dest_address,
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(endpoint, params=params)
    routes = response.json().get("routes", [])
    if routes:
        eta = routes[0]["legs"][0]["duration"]["text"]
        logger.info(f"ETA calculated: {eta}")
        return eta
    logger.warning("ETA calculation failed")
    return "ETA unavailable"