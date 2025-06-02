from flask import Blueprint, request, render_template, redirect
from services.loads_service import get_unassigned_loads, assign_driver_to_load
from services.motive_api import get_active_driver_locations

assignments_bp = Blueprint('assignments', __name__)

@assignments_bp.route("/assign", methods=["GET", "POST"])
def assign():
    if request.method == "POST":
        load_id = request.form["load_id"]
        driver_name = request.form["driver_name"]
        assign_driver_to_load(load_id, driver_name)
        return redirect("/assign")

    unassigned = get_unassigned_loads()
    drivers = get_active_driver_locations()
    return render_template("assign_load.html", loads=unassigned, drivers=drivers)
