from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.motive_api import get_vehicle_locations
from services.loads_service import load_all, save_all
import json
import os

imports_bp = Blueprint("imports", __name__)

@imports_bp.route("/imports/drivers-vehicles", methods=["GET", "POST"])
def import_drivers_vehicles():
    if request.method == "POST":
        selected_drivers = request.form.getlist("drivers")
        selected_vehicles = request.form.getlist("vehicles")

        # Load existing drivers from JSON
        drivers_file = "drivers.json"
        if os.path.exists(drivers_file):
            with open(drivers_file, 'r') as f:
                existing_drivers = json.load(f)
        else:
            existing_drivers = []

        # Add selected drivers if they don't already exist
        existing_names = [d["name"] for d in existing_drivers]
        for name in selected_drivers:
            if name not in existing_names:
                existing_drivers.append({
                    "name": name, 
                    "loads_completed": 0, 
                    "on_time_pct": 100, 
                    "badges": []
                })

        # Save updated drivers list
        with open(drivers_file, 'w') as f:
            json.dump(existing_drivers, f, indent=2)

        flash(f"Successfully imported {len(selected_drivers)} drivers and {len(selected_vehicles)} vehicles", "success")
        return redirect(url_for("imports.import_drivers_vehicles"))

    try:
        # Get data from Motive API
        motive_data = get_vehicle_locations()
        driver_names = list({v["driver_name"] for v in motive_data if v.get("driver_name")})
        vehicle_names = list({v["vehicle_name"] for v in motive_data if v.get("vehicle_name")})
        
        return render_template("import_selector.html", 
                             drivers=driver_names, 
                             vehicles=vehicle_names,
                             has_data=True)
    except Exception as e:
        # If Motive API fails, show empty form with error message
        return render_template("import_selector.html", 
                             drivers=[], 
                             vehicles=[],
                             has_data=False,
                             error_message="Unable to connect to Motive API. Please check your API credentials.")