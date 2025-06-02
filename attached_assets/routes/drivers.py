from flask import Blueprint, jsonify
from services.motive_api import get_active_driver_locations
from services.google_maps_api import get_eta

drivers_bp = Blueprint('drivers', __name__)

@drivers_bp.route("/api/drivers/locations")
def driver_locations():
    drivers = get_active_driver_locations()
    destination = "123 Delivery St, Dallas TX"
    for d in drivers:
        d["eta"] = get_eta(d["latitude"], d["longitude"], destination)
    return jsonify(drivers)
