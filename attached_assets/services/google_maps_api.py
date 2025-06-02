import requests
import os

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_eta(origin_lat, origin_lng, dest_address):
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
        return eta
    return "ETA unavailable"
