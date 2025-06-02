from flask import Blueprint, render_template, request, redirect, url_for
from services.motive_oauth import get_vehicle_locations
from utils.storage import save_json, load_json

imports_bp = Blueprint("imports", __name__)

@imports_bp.route("/imports/drivers-vehicles", methods=["GET", "POST"])
def import_drivers_vehicles():
    if request.method == "POST":
        selected_drivers = request.form.getlist("drivers")
        selected_vehicles = request.form.getlist("vehicles")

        existing = load_json("drivers.json")
        for name in selected_drivers:
            if name not in [d["name"] for d in existing]:
                existing.append({"name": name, "loads_completed": 0, "on_time_pct": 100, "badges": []})

        save_json("drivers.json", existing)
        return redirect(url_for("imports.import_drivers_vehicles"))

    motive_data = get_vehicle_locations()
    driver_names = list({v["driver_name"] for v in motive_data if v.get("driver_name")})
    vehicle_names = list({v["vehicle_name"] for v in motive_data if v.get("vehicle_name")})
    return render_template("import_selector.html", drivers=driver_names, vehicles=vehicle_names)
