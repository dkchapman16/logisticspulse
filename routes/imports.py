from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.motive_oauth import get_driver_vehicle_list
from utils.storage import save_json, load_json

imports_bp = Blueprint("imports", __name__)

@imports_bp.route("/imports/drivers-vehicles", methods=["GET", "POST"])
def import_drivers_vehicles():
    if request.method == "POST":
        selected_drivers = request.form.getlist("drivers")
        selected_vehicles = request.form.getlist("vehicles")

        # Load existing drivers and add selected ones
        existing = load_json("drivers.json")
        existing_names = [d["name"] for d in existing]
        
        new_drivers_count = 0
        for name in selected_drivers:
            if name not in existing_names:
                existing.append({
                    "name": name, 
                    "loads_completed": 0, 
                    "on_time_pct": 100, 
                    "badges": []
                })
                new_drivers_count += 1

        save_json("drivers.json", existing)
        
        if new_drivers_count > 0:
            flash(f"Successfully imported {new_drivers_count} new drivers", "success")
        else:
            flash("No new drivers were imported (they may already exist)", "info")
            
        return redirect(url_for("imports.import_drivers_vehicles"))

    # Get driver and vehicle lists from Motive API
    try:
        driver_names, vehicle_names = get_driver_vehicle_list()
        has_data = len(driver_names) > 0 or len(vehicle_names) > 0
        
        return render_template("import_selector.html", 
                             drivers=driver_names, 
                             vehicles=vehicle_names,
                             has_data=has_data,
                             error_message=None if has_data else "No drivers or vehicles found in Motive API")
    except Exception as e:
        return render_template("import_selector.html", 
                             drivers=[], 
                             vehicles=[],
                             has_data=False,
                             error_message="Unable to connect to Motive API. Please check your API credentials.")