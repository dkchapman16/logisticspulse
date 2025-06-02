from flask import Blueprint, request, render_template, redirect, flash
from services.loads_service import get_unassigned_loads, assign_driver_to_load
from services.motive_api import get_active_driver_locations
from services.logger import setup_logger

logger = setup_logger(__name__)
assignments_bp = Blueprint('assignments', __name__)

@assignments_bp.route("/assign", methods=["GET", "POST"])
def assign():
    if request.method == "POST":
        load_id = request.form["load_id"]
        driver_name = request.form["driver_name"]
        assign_driver_to_load(load_id, driver_name)
        flash(f"Successfully assigned Load #{load_id} to {driver_name}", "success")
        return redirect("/assign")

    unassigned = get_unassigned_loads()
    
    # Try to get drivers from Motive API with fallback
    try:
        drivers = get_active_driver_locations()
        logger.info(f"Retrieved {len(drivers)} drivers from Motive API")
    except Exception as e:
        logger.warning(f"Failed to fetch drivers from Motive API: {e}")
        # Fallback to sample drivers for demo purposes
        drivers = [
            {"name": "John Smith", "status": "available"},
            {"name": "Maria Garcia", "status": "available"}, 
            {"name": "Mike Johnson", "status": "available"},
            {"name": "Sarah Williams", "status": "available"}
        ]
        flash("Using demo driver data - Motive API connection needed for live data", "warning")
    
    return render_template("assign_load.html", loads=unassigned, drivers=drivers)
