from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from services.motive_api_key import get_drivers, get_vehicles
from models import Driver, Vehicle, db
from app import app

imports_bp = Blueprint("imports", __name__)

@imports_bp.route("/imports/drivers-vehicles", methods=["GET", "POST"])
def import_drivers_vehicles():
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "sync_motive":
            try:
                # Get data from Motive API
                motive_drivers = get_drivers()
                motive_vehicles = get_vehicles()
                
                drivers_added = 0
                vehicles_added = 0
                
                # Add only active drivers to database
                for driver_item in motive_drivers:
                    user_data = driver_item.get('user', {})
                    motive_id = str(user_data.get('id'))
                    user_status = user_data.get('status', '')
                    
                    # Only process active drivers (role=driver, status=active)
                    if user_status != 'active' or user_data.get('role') != 'driver':
                        continue
                    
                    first_name = user_data.get('first_name', '').strip()
                    last_name = user_data.get('last_name', '').strip()
                    name = f"{first_name} {last_name}".strip()
                    
                    if not name or not motive_id:
                        continue
                    
                    # Skip if already exists by Motive ID or exact name match
                    existing_by_id = Driver.query.filter_by(motive_driver_id=motive_id).first()
                    existing_by_name = Driver.query.filter_by(name=name).first()
                    
                    if existing_by_id or existing_by_name:
                        continue
                        
                    new_driver = Driver(
                        name=name,
                        motive_driver_id=motive_id,
                        email=user_data.get('email', ''),
                        phone=user_data.get('phone', ''),
                        company='Hitched Logistics LLC',
                        status='active'
                    )
                    db.session.add(new_driver)
                    drivers_added += 1
                
                # Add only active vehicles to database
                for vehicle_item in motive_vehicles:
                    vehicle_data = vehicle_item.get('vehicle', {})
                    motive_id = str(vehicle_data.get('id'))
                    vehicle_status = vehicle_data.get('status', '')
                    license_plate = vehicle_data.get('license_plate_number', '').strip()
                    
                    # Only process active vehicles
                    if vehicle_status != 'active':
                        continue
                    
                    if not motive_id:
                        continue
                    
                    # Skip if already exists by Motive ID or license plate
                    existing_by_id = Vehicle.query.filter_by(motive_vehicle_id=motive_id).first()
                    existing_by_plate = None
                    if license_plate:
                        existing_by_plate = Vehicle.query.filter_by(license_plate=license_plate).first()
                    
                    if existing_by_id or existing_by_plate:
                        continue
                        
                    new_vehicle = Vehicle(
                        motive_vehicle_id=motive_id,
                        license_plate=license_plate,
                        make=vehicle_data.get('make', ''),
                        model=vehicle_data.get('model', ''),
                        year=vehicle_data.get('year'),
                        status='active'
                    )
                    db.session.add(new_vehicle)
                    vehicles_added += 1
                
                db.session.commit()
                
                if drivers_added > 0 or vehicles_added > 0:
                    flash(f"Successfully synced {drivers_added} drivers and {vehicles_added} vehicles from Motive", "success")
                else:
                    flash("All Motive data already exists in database", "info")
                    
            except Exception as e:
                db.session.rollback()
                flash(f"Error syncing from Motive: {str(e)}", "danger")
            
            return redirect(url_for("imports.import_drivers_vehicles"))

    # Get data for display
    try:
        motive_drivers = get_drivers()
        motive_vehicles = get_vehicles()
        
        # Format active driver names for display (role=driver only)
        driver_names = []
        for driver_item in motive_drivers:
            user_data = driver_item.get('user', {})
            # Only show active drivers (role=driver, status=active)
            if user_data.get('status') != 'active' or user_data.get('role') != 'driver':
                continue
            first_name = user_data.get('first_name', '').strip()
            last_name = user_data.get('last_name', '').strip()
            name = f"{first_name} {last_name}".strip()
            if name:
                driver_names.append(name)
        
        # Format active vehicle names for display
        vehicle_names = []
        for vehicle_item in motive_vehicles:
            vehicle_data = vehicle_item.get('vehicle', {})
            # Only show active vehicles
            if vehicle_data.get('status') != 'active':
                continue
            make = vehicle_data.get('make', '')
            model = vehicle_data.get('model', '')
            number = vehicle_data.get('number', '')
            name = f"{make} {model} #{number}".strip()
            if name:
                vehicle_names.append(name)
        
        has_data = len(driver_names) > 0 or len(vehicle_names) > 0
        
        return render_template("import_selector.html", 
                             drivers=driver_names, 
                             vehicles=vehicle_names,
                             has_data=has_data,
                             drivers_count=len(driver_names),
                             vehicles_count=len(vehicle_names),
                             error_message=None if has_data else "No drivers or vehicles found in Motive API")
                             
    except Exception as e:
        return render_template("import_selector.html", 
                             drivers=[], 
                             vehicles=[],
                             has_data=False,
                             drivers_count=0,
                             vehicles_count=0,
                             error_message="Unable to connect to Motive API. Please check your API credentials.")