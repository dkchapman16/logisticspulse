from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime
from app import db
from models import Facility, Load
from services.geofencing import check_geofence_entry

geofencing_bp = Blueprint('geofencing', __name__)

@geofencing_bp.route('/geofencing')
def index():
    """Show geofencing management interface"""
    return render_template('geofencing.html')

@geofencing_bp.route('/geofencing/facilities')
def get_facilities():
    """API endpoint to get all facilities with geofences"""
    facilities = Facility.query.all()
    
    facilities_data = [{
        'id': f.id,
        'name': f.name,
        'address': f.address,
        'city': f.city,
        'state': f.state,
        'zip_code': f.zip_code,
        'lat': f.lat,
        'lng': f.lng,
        'geofence_radius': f.geofence_radius,
        'client': f.client.name if f.client else 'Unknown'
    } for f in facilities]
    
    return jsonify(facilities_data)

@geofencing_bp.route('/geofencing/facility/<int:facility_id>', methods=['GET', 'PUT'])
def facility_detail(facility_id):
    """Get or update a facility's geofence"""
    facility = Facility.query.get_or_404(facility_id)
    
    if request.method == 'PUT':
        try:
            data = request.json
            
            # Update geofence radius
            if 'geofence_radius' in data:
                facility.geofence_radius = float(data['geofence_radius'])
            
            # Update coordinates if provided
            if 'lat' in data and 'lng' in data:
                facility.lat = float(data['lat'])
                facility.lng = float(data['lng'])
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'facility': {
                    'id': facility.id,
                    'name': facility.name,
                    'lat': facility.lat,
                    'lng': facility.lng,
                    'geofence_radius': facility.geofence_radius
                }
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    # GET request
    facility_data = {
        'id': facility.id,
        'name': facility.name,
        'address': facility.address,
        'city': facility.city,
        'state': facility.state,
        'zip_code': facility.zip_code,
        'lat': facility.lat,
        'lng': facility.lng,
        'geofence_radius': facility.geofence_radius,
        'client': {
            'id': facility.client.id,
            'name': facility.client.name
        } if facility.client else None
    }
    
    return jsonify(facility_data)

@geofencing_bp.route('/geofencing/check', methods=['POST'])
def check_geofence():
    """Check if a vehicle has entered or exited a geofence"""
    try:
        data = request.json
        
        load_id = data.get('load_id')
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not load_id or not lat or not lng:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        load = Load.query.get_or_404(load_id)
        
        # Check if the vehicle has entered/exited a geofence
        result = check_geofence_entry(load, float(lat), float(lng))
        
        # If status has changed, update the load record
        if result['status_changed']:
            db.session.commit()
        
        return jsonify(result)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@geofencing_bp.route('/geofencing/create-facility', methods=['POST'])
def create_facility():
    """Create a new facility with geofence"""
    try:
        data = request.form
        
        # Check required fields
        required_fields = ['name', 'address', 'client_id', 'lat', 'lng']
        for field in required_fields:
            if not data.get(field):
                flash(f'Missing required field: {field}', 'danger')
                return redirect(url_for('geofencing.index'))
        
        # Create new facility
        new_facility = Facility(
            name=data['name'],
            address=data['address'],
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip_code', ''),
            lat=float(data['lat']),
            lng=float(data['lng']),
            geofence_radius=float(data.get('geofence_radius', 0.2)),
            client_id=int(data['client_id'])
        )
        
        db.session.add(new_facility)
        db.session.commit()
        
        flash('Facility created successfully', 'success')
        return redirect(url_for('geofencing.index'))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating facility: {str(e)}', 'danger')
        return redirect(url_for('geofencing.index'))
