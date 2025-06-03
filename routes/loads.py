from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
from app import db
from models import Load, Driver, Vehicle, Client, Facility, LocationUpdate
from services.pdf_extractor_ai_only import extract_from_pdf
from services.google_maps_api import get_eta

loads_bp = Blueprint('loads', __name__)

@loads_bp.route('/loads')
def index():
    """Show all loads"""
    return render_template('loads.html')

@loads_bp.route('/loads/data')
def get_loads():
    """API endpoint to get all loads with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', None)
    
    query = Load.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Load.status == status_filter)
    
    # Order by most recent first
    query = query.order_by(Load.created_at.desc())
    
    # Paginate results
    loads_page = query.paginate(page=page, per_page=per_page)
    
    # Format response data
    loads_data = []
    for load in loads_page.items:
        driver_name = load.driver.name if load.driver else "Unassigned"
        pickup_facility = load.pickup_facility.name if load.pickup_facility else "Unknown"
        delivery_facility = load.delivery_facility.name if load.delivery_facility else "Unknown"
        
        loads_data.append({
            'id': load.id,
            'reference_number': load.reference_number,
            'status': load.status,
            'driver': driver_name,
            'pickup': pickup_facility,
            'scheduled_pickup': load.scheduled_pickup_time.strftime('%Y-%m-%d %H:%M') if load.scheduled_pickup_time else None,
            'delivery': delivery_facility,
            'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M') if load.scheduled_delivery_time else None,
            'on_time_pickup': load.pickup_on_time,
            'on_time_delivery': load.delivery_on_time,
            'current_eta': load.current_eta.strftime('%Y-%m-%d %H:%M') if load.current_eta else None
        })
    
    return jsonify({
        'loads': loads_data,
        'page': page,
        'per_page': per_page,
        'total': loads_page.total,
        'pages': loads_page.pages
    })

@loads_bp.route('/loads/<int:load_id>')
def load_detail(load_id):
    """Show load details"""
    load = Load.query.get_or_404(load_id)
    return render_template('load_detail.html', load=load)

@loads_bp.route('/loads/<int:load_id>/data')
def get_load_data(load_id):
    """API endpoint to get detailed load data"""
    load = Load.query.get_or_404(load_id)
    
    # Get the 10 most recent location updates
    recent_locations = LocationUpdate.query.filter_by(load_id=load.id).order_by(LocationUpdate.timestamp.desc()).limit(10).all()
    location_data = [{
        'timestamp': update.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        'lat': update.lat,
        'lng': update.lng,
        'speed': update.speed,
        'heading': update.heading
    } for update in recent_locations]
    
    # Format the load data
    load_data = {
        'id': load.id,
        'reference_number': load.reference_number,
        'status': load.status,
        'ratecon_url': load.ratecon_url,
        
        'client': {
            'id': load.client.id,
            'name': load.client.name
        } if load.client else None,
        
        'driver': {
            'id': load.driver.id,
            'name': load.driver.name,
            'phone': load.driver.phone,
            'email': load.driver.email
        } if load.driver else None,
        
        'vehicle': {
            'id': load.vehicle.id,
            'plate': load.vehicle.license_plate,
            'make': load.vehicle.make,
            'model': load.vehicle.model
        } if load.vehicle else None,
        
        'pickup': {
            'facility_id': load.pickup_facility.id,
            'name': load.pickup_facility.name,
            'address': load.pickup_facility.address,
            'city': load.pickup_facility.city,
            'state': load.pickup_facility.state,
            'zip': load.pickup_facility.zip_code,
            'lat': load.pickup_facility.lat,
            'lng': load.pickup_facility.lng,
            'scheduled_time': load.scheduled_pickup_time.strftime('%Y-%m-%d %H:%M') if load.scheduled_pickup_time else None,
            'actual_arrival': load.actual_pickup_arrival.strftime('%Y-%m-%d %H:%M') if load.actual_pickup_arrival else None,
            'actual_departure': load.actual_pickup_departure.strftime('%Y-%m-%d %H:%M') if load.actual_pickup_departure else None,
            'on_time': load.pickup_on_time
        } if load.pickup_facility else None,
        
        'delivery': {
            'facility_id': load.delivery_facility.id,
            'name': load.delivery_facility.name,
            'address': load.delivery_facility.address,
            'city': load.delivery_facility.city,
            'state': load.delivery_facility.state,
            'zip': load.delivery_facility.zip_code,
            'lat': load.delivery_facility.lat,
            'lng': load.delivery_facility.lng,
            'scheduled_time': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M') if load.scheduled_delivery_time else None,
            'actual_arrival': load.actual_delivery_arrival.strftime('%Y-%m-%d %H:%M') if load.actual_delivery_arrival else None,
            'actual_departure': load.actual_delivery_departure.strftime('%Y-%m-%d %H:%M') if load.actual_delivery_departure else None,
            'on_time': load.delivery_on_time
        } if load.delivery_facility else None,
        
        'current_eta': load.current_eta.strftime('%Y-%m-%d %H:%M') if load.current_eta else None,
        'created_at': load.created_at.strftime('%Y-%m-%d %H:%M'),
        'last_locations': location_data
    }
    
    return jsonify(load_data)

@loads_bp.route('/loads/create', methods=['GET', 'POST'])
def create_load():
    """Create a new load"""
    if request.method == 'POST':
        try:
            data = request.form
            
            # Check if required fields are present
            required_fields = ['reference_number', 'client_id', 'pickup_facility_id', 
                               'scheduled_pickup_time', 'delivery_facility_id', 'scheduled_delivery_time']
            
            for field in required_fields:
                if not data.get(field):
                    flash(f'Missing required field: {field}', 'danger')
                    return redirect(url_for('loads.create_load'))
            
            # Parse datetime fields
            scheduled_pickup = datetime.strptime(data['scheduled_pickup_time'], '%Y-%m-%dT%H:%M')
            scheduled_delivery = datetime.strptime(data['scheduled_delivery_time'], '%Y-%m-%dT%H:%M')
            
            # Create new load object
            new_load = Load(
                reference_number=data['reference_number'],
                client_id=data['client_id'],
                pickup_facility_id=data['pickup_facility_id'],
                scheduled_pickup_time=scheduled_pickup,
                delivery_facility_id=data['delivery_facility_id'],
                scheduled_delivery_time=scheduled_delivery,
                status='scheduled'
            )
            
            # Optional fields
            if data.get('driver_id'):
                new_load.driver_id = data['driver_id']
            
            if data.get('vehicle_id'):
                new_load.vehicle_id = data['vehicle_id']
            
            # Save to database
            db.session.add(new_load)
            db.session.commit()
            
            flash('Load created successfully', 'success')
            return redirect(url_for('loads.load_detail', load_id=new_load.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating load: {str(e)}', 'danger')
            return redirect(url_for('loads.create_load'))
    
    # GET request - render form
    clients = Client.query.all()
    facilities = Facility.query.all()
    drivers = Driver.query.filter_by(status='active').all()
    vehicles = Vehicle.query.filter_by(status='active').all()
    
    return render_template('load_detail.html', 
                          clients=clients, 
                          facilities=facilities, 
                          drivers=drivers, 
                          vehicles=vehicles,
                          load=None)  # None indicates this is a create form

@loads_bp.route('/loads/<int:load_id>/update', methods=['POST'])
def update_load(load_id):
    """Update an existing load"""
    load = Load.query.get_or_404(load_id)
    
    try:
        data = request.form
        
        # Update basic fields
        if data.get('reference_number'):
            load.reference_number = data['reference_number']
        
        if data.get('client_id'):
            load.client_id = data['client_id']
        
        if data.get('driver_id'):
            load.driver_id = data['driver_id']
        
        if data.get('vehicle_id'):
            load.vehicle_id = data['vehicle_id']
        
        if data.get('status'):
            load.status = data['status']
        
        # Update pickup details
        if data.get('pickup_facility_id'):
            load.pickup_facility_id = data['pickup_facility_id']
        
        if data.get('scheduled_pickup_time'):
            load.scheduled_pickup_time = datetime.strptime(data['scheduled_pickup_time'], '%Y-%m-%dT%H:%M')
        
        if data.get('actual_pickup_arrival'):
            load.actual_pickup_arrival = datetime.strptime(data['actual_pickup_arrival'], '%Y-%m-%dT%H:%M')
        
        if data.get('actual_pickup_departure'):
            load.actual_pickup_departure = datetime.strptime(data['actual_pickup_departure'], '%Y-%m-%dT%H:%M')
        
        # Update delivery details
        if data.get('delivery_facility_id'):
            load.delivery_facility_id = data['delivery_facility_id']
        
        if data.get('scheduled_delivery_time'):
            load.scheduled_delivery_time = datetime.strptime(data['scheduled_delivery_time'], '%Y-%m-%dT%H:%M')
        
        if data.get('actual_delivery_arrival'):
            load.actual_delivery_arrival = datetime.strptime(data['actual_delivery_arrival'], '%Y-%m-%dT%H:%M')
        
        if data.get('actual_delivery_departure'):
            load.actual_delivery_departure = datetime.strptime(data['actual_delivery_departure'], '%Y-%m-%dT%H:%M')
        
        # Save changes
        db.session.commit()
        
        # If we have a delivery facility and driver but no ETA, calculate it
        if load.delivery_facility and load.driver and not load.current_eta and load.status == 'in_transit':
            vehicle = load.vehicle
            if vehicle and vehicle.current_lat and vehicle.current_lng:
                destination = f"{load.delivery_facility.lat},{load.delivery_facility.lng}"
                origin = f"{vehicle.current_lat},{vehicle.current_lng}"
                
                # Get ETA from Google Maps API
                eta_data = get_eta(origin, destination)
                if eta_data and 'eta' in eta_data:
                    load.current_eta = eta_data['eta']
                    db.session.commit()
        
        flash('Load updated successfully', 'success')
        return redirect(url_for('loads.load_detail', load_id=load.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating load: {str(e)}', 'danger')
        return redirect(url_for('loads.load_detail', load_id=load.id))

@loads_bp.route('/loads/upload-ratecon', methods=['POST'])
def upload_ratecon():
    """Upload and process a RateCon PDF"""
    try:
        if 'ratecon_file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['ratecon_file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and file.filename.lower().endswith('.pdf'):
            # Extract data from PDF
            extracted_data = extract_from_pdf(file)
            
            # Debug what AI extracted
            print(f"🔍 AI EXTRACTED: {extracted_data}")
            print(f"🔍 PICKUP: {extracted_data.get('pickup', 'None')}")
            print(f"🔍 DELIVERY: {extracted_data.get('delivery', 'None')}")
            
            # Return the extracted data with success status
            # Store extracted data in session for form display
            from flask import session
            session['extracted_data'] = extracted_data
            
            return jsonify({
                'success': True,
                'message': 'PDF processed successfully',
                'data': extracted_data,
                'redirect_url': '/loads/create-from-ai'
            })
            
        else:
            return jsonify({'error': 'File must be a PDF'}), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error processing PDF: {str(e)}'
        }), 500

@loads_bp.route('/loads/create-from-ai', methods=['GET', 'POST'])
def create_from_ai():
    """Display form with AI-extracted data or process the submission"""
    from flask import session
    
    if request.method == 'POST':
        try:
            data = request.form
            
            # Create or find client
            client_name = data.get('customer')
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                client = Client(name=client_name)
                db.session.add(client)
                db.session.flush()  # Get the ID
            
            # Create or find pickup facility
            pickup_name = data.get('pickup_facility')
            pickup_address = data.get('pickup_address')
            pickup_facility = Facility.query.filter_by(name=pickup_name).first()
            if not pickup_facility:
                pickup_facility = Facility(
                    name=pickup_name,
                    address=pickup_address,
                    client_id=client.id
                )
                db.session.add(pickup_facility)
                db.session.flush()
            
            # Create or find delivery facility
            delivery_name = data.get('delivery_facility')
            delivery_address = data.get('delivery_address')
            delivery_facility = Facility.query.filter_by(name=delivery_name).first()
            if not delivery_facility:
                delivery_facility = Facility(
                    name=delivery_name,
                    address=delivery_address,
                    client_id=client.id
                )
                db.session.add(delivery_facility)
                db.session.flush()
            
            # Parse datetime fields
            scheduled_pickup = datetime.strptime(data['scheduled_pickup_time'], '%Y-%m-%dT%H:%M')
            scheduled_delivery = datetime.strptime(data['scheduled_delivery_time'], '%Y-%m-%dT%H:%M')
            
            # Find driver if selected
            driver = None
            if data.get('driver'):
                driver = Driver.query.filter_by(name=data['driver']).first()
            
            # Create new load
            new_load = Load(
                reference_number=data['reference_number'],
                client_id=client.id,
                pickup_facility_id=pickup_facility.id,
                scheduled_pickup_time=scheduled_pickup,
                delivery_facility_id=delivery_facility.id,
                scheduled_delivery_time=scheduled_delivery,
                driver_id=driver.id if driver else None,
                status='scheduled'
            )
            
            db.session.add(new_load)
            db.session.commit()
            
            # Clear extracted data from session
            session.pop('extracted_data', None)
            
            flash('Load created successfully!', 'success')
            return redirect(url_for('loads.index'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating load: {str(e)}', 'danger')
            return redirect(url_for('loads.create_from_ai'))
    
    # GET request - show the form
    extracted_data = session.get('extracted_data')
    if not extracted_data:
        flash('No extracted data found. Please upload a PDF first.', 'warning')
        return redirect(url_for('loads.index'))
    
    # Get available drivers (fallback to sample data if API fails)
    drivers = ["Sydney Chapman", "Bryan Chapman"]
    
    return render_template('create_load_from_ai.html', 
                          data=extracted_data, 
                          drivers=drivers)

@loads_bp.route('/loads/<int:load_id>/update-location', methods=['POST'])
def update_location(load_id):
    """Manually update a load's location"""
    load = Load.query.get_or_404(load_id)
    
    try:
        data = request.json
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        # Update vehicle location if available
        if load.vehicle:
            load.vehicle.current_lat = lat
            load.vehicle.current_lng = lng
            load.vehicle.last_updated = datetime.utcnow()
        
        # Create a location update record
        location_update = LocationUpdate(
            load_id=load.id,
            lat=lat,
            lng=lng,
            speed=data.get('speed', 0),
            heading=data.get('heading', 0)
        )
        
        db.session.add(location_update)
        
        # Update ETA if delivery facility exists
        if load.delivery_facility and load.status == 'in_transit':
            destination = f"{load.delivery_facility.lat},{load.delivery_facility.lng}"
            origin = f"{lat},{lng}"
            
            # Get ETA from Google Maps API
            eta_data = get_eta(origin, destination)
            if eta_data and 'eta' in eta_data:
                load.current_eta = eta_data['eta']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'current_eta': load.current_eta.strftime('%Y-%m-%d %H:%M') if load.current_eta else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
