from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import db, Driver, Truck, Trailer, AssetAssignment
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

assets_bp = Blueprint('assets', __name__, url_prefix='/assets')

@assets_bp.route('/')
def index():
    """Assets management main page"""
    return render_template('assets/index.html')

@assets_bp.route('/drivers')
def drivers():
    """Drivers management page"""
    return render_template('assets/drivers.html')

@assets_bp.route('/trucks')
def trucks():
    """Trucks management page"""
    return render_template('assets/trucks.html')

@assets_bp.route('/trailers')
def trailers():
    """Trailers management page"""
    return render_template('assets/trailers.html')

# API Endpoints for Drivers
@assets_bp.route('/api/drivers')
def get_drivers():
    """Get all drivers with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        query = Driver.query
        
        if search:
            query = query.filter(Driver.name.ilike(f'%{search}%'))
        
        if status_filter:
            query = query.filter(Driver.status == status_filter)
        
        drivers = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        drivers_data = []
        for driver in drivers.items:
            # Get current assignments
            current_truck = None
            current_trailer = None
            current_assignment = AssetAssignment.query.filter_by(
                driver_id=driver.id, 
                current=True
            ).first()
            
            if current_assignment:
                if current_assignment.truck_id:
                    truck = Truck.query.get(current_assignment.truck_id)
                    current_truck = truck.truck_number if truck else None
                if current_assignment.trailer_id:
                    trailer = Trailer.query.get(current_assignment.trailer_id)
                    current_trailer = trailer.trailer_number if trailer else None
            
            drivers_data.append({
                'id': driver.id,
                'name': driver.name,
                'phone': driver.phone,
                'email': driver.email,
                'status': driver.status,
                'current_truck': current_truck,
                'current_trailer': current_trailer,
                'created_at': driver.created_at.strftime('%Y-%m-%d') if driver.created_at else None
            })
        
        return jsonify({
            'drivers': drivers_data,
            'total': drivers.total,
            'pages': drivers.pages,
            'current_page': drivers.page,
            'has_next': drivers.has_next,
            'has_prev': drivers.has_prev
        })
    
    except Exception as e:
        logger.error(f"Error fetching drivers: {e}")
        return jsonify({'error': 'Failed to fetch drivers'}), 500

@assets_bp.route('/api/drivers', methods=['POST'])
def create_driver():
    """Create a new driver"""
    try:
        data = request.get_json()
        
        driver = Driver(
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            company=data.get('company', 'Hitched Logistics LLC'),
            status=data.get('status', 'active')
        )
        
        db.session.add(driver)
        db.session.commit()
        
        return jsonify({
            'message': 'Driver created successfully',
            'driver': {
                'id': driver.id,
                'name': driver.name,
                'phone': driver.phone,
                'email': driver.email,
                'status': driver.status
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating driver: {e}")
        return jsonify({'error': 'Failed to create driver'}), 500

# API Endpoints for Trucks
@assets_bp.route('/api/trucks')
def get_trucks():
    """Get all trucks with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        query = Truck.query
        
        if search:
            query = query.filter(Truck.truck_number.ilike(f'%{search}%'))
        
        if status_filter:
            query = query.filter(Truck.status == status_filter)
        
        trucks = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        trucks_data = []
        for truck in trucks.items:
            # Get current assignment
            current_driver = None
            current_assignment = AssetAssignment.query.filter_by(
                truck_id=truck.id, 
                current=True
            ).first()
            
            if current_assignment:
                driver = Driver.query.get(current_assignment.driver_id)
                current_driver = driver.name if driver else None
            
            trucks_data.append({
                'id': truck.id,
                'truck_number': truck.truck_number,
                'make': truck.make,
                'model': truck.model,
                'year': truck.year,
                'status': truck.status,
                'current_driver': current_driver,
                'vin': truck.vin,
                'license_plate': truck.license_plate
            })
        
        return jsonify({
            'trucks': trucks_data,
            'total': trucks.total,
            'pages': trucks.pages,
            'current_page': trucks.page
        })
    
    except Exception as e:
        logger.error(f"Error fetching trucks: {e}")
        return jsonify({'error': 'Failed to fetch trucks'}), 500

@assets_bp.route('/api/trucks', methods=['POST'])
def create_truck():
    """Create a new truck"""
    try:
        data = request.get_json()
        
        truck = Truck(
            truck_number=data.get('truck_number'),
            make=data.get('make'),
            model=data.get('model'),
            year=data.get('year'),
            vin=data.get('vin'),
            color=data.get('color'),
            license_plate=data.get('license_plate'),
            state=data.get('state'),
            status=data.get('status', 'active'),
            ownership_type=data.get('ownership_type'),
            fuel_card=data.get('fuel_card'),
            notes=data.get('notes')
        )
        
        db.session.add(truck)
        db.session.commit()
        
        return jsonify({
            'message': 'Truck created successfully',
            'truck': {
                'id': truck.id,
                'truck_number': truck.truck_number,
                'make': truck.make,
                'model': truck.model,
                'year': truck.year,
                'status': truck.status
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating truck: {e}")
        return jsonify({'error': 'Failed to create truck'}), 500

# API Endpoints for Trailers
@assets_bp.route('/api/trailers')
def get_trailers():
    """Get all trailers with pagination and filtering"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', '')
        
        query = Trailer.query
        
        if search:
            query = query.filter(Trailer.trailer_number.ilike(f'%{search}%'))
        
        if status_filter:
            query = query.filter(Trailer.status == status_filter)
        
        trailers = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        trailers_data = []
        for trailer in trailers.items:
            # Get current assignment
            current_driver = None
            current_assignment = AssetAssignment.query.filter_by(
                trailer_id=trailer.id, 
                current=True
            ).first()
            
            if current_assignment:
                driver = Driver.query.get(current_assignment.driver_id)
                current_driver = driver.name if driver else None
            
            trailers_data.append({
                'id': trailer.id,
                'trailer_number': trailer.trailer_number,
                'trailer_type': trailer.trailer_type,
                'length': trailer.length,
                'status': trailer.status,
                'current_driver': current_driver,
                'vin': trailer.vin,
                'license_plate': trailer.license_plate
            })
        
        return jsonify({
            'trailers': trailers_data,
            'total': trailers.total,
            'pages': trailers.pages,
            'current_page': trailers.page
        })
    
    except Exception as e:
        logger.error(f"Error fetching trailers: {e}")
        return jsonify({'error': 'Failed to fetch trailers'}), 500

@assets_bp.route('/api/trailers', methods=['POST'])
def create_trailer():
    """Create a new trailer"""
    try:
        data = request.get_json()
        
        trailer = Trailer(
            trailer_number=data.get('trailer_number'),
            trailer_type=data.get('trailer_type'),
            length=data.get('length'),
            model=data.get('model'),
            vin=data.get('vin'),
            width=data.get('width'),
            license_plate=data.get('license_plate'),
            state=data.get('state'),
            status=data.get('status', 'active'),
            ownership_type=data.get('ownership_type'),
            notes=data.get('notes')
        )
        
        db.session.add(trailer)
        db.session.commit()
        
        return jsonify({
            'message': 'Trailer created successfully',
            'trailer': {
                'id': trailer.id,
                'trailer_number': trailer.trailer_number,
                'trailer_type': trailer.trailer_type,
                'length': trailer.length,
                'status': trailer.status
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating trailer: {e}")
        return jsonify({'error': 'Failed to create trailer'}), 500

# Asset Assignment Endpoints
@assets_bp.route('/api/assignments', methods=['POST'])
def create_assignment():
    """Create or update asset assignment for a driver"""
    try:
        data = request.get_json()
        driver_id = data.get('driver_id')
        truck_id = data.get('truck_id')
        trailer_id = data.get('trailer_id')
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        end_date = None
        
        if data.get('end_date'):
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        
        # End current assignments for this driver
        current_assignments = AssetAssignment.query.filter_by(
            driver_id=driver_id, 
            current=True
        ).all()
        
        for assignment in current_assignments:
            assignment.current = False
            assignment.end_date = start_date
        
        # Create new assignment
        new_assignment = AssetAssignment(
            driver_id=driver_id,
            truck_id=truck_id if truck_id else None,
            trailer_id=trailer_id if trailer_id else None,
            start_date=start_date,
            end_date=end_date,
            current=end_date is None  # Current if no end date
        )
        
        db.session.add(new_assignment)
        db.session.commit()
        
        return jsonify({'message': 'Assignment created successfully'}), 201
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating assignment: {e}")
        return jsonify({'error': 'Failed to create assignment'}), 500

@assets_bp.route('/api/assignments/<int:driver_id>')
def get_driver_assignments(driver_id):
    """Get assignment history for a specific driver"""
    try:
        assignments = AssetAssignment.query.filter_by(driver_id=driver_id).order_by(
            AssetAssignment.start_date.desc()
        ).all()
        
        assignments_data = []
        for assignment in assignments:
            truck_info = None
            trailer_info = None
            
            if assignment.truck_id:
                truck = Truck.query.get(assignment.truck_id)
                truck_info = {
                    'id': truck.id,
                    'truck_number': truck.truck_number,
                    'make': truck.make,
                    'model': truck.model
                } if truck else None
            
            if assignment.trailer_id:
                trailer = Trailer.query.get(assignment.trailer_id)
                trailer_info = {
                    'id': trailer.id,
                    'trailer_number': trailer.trailer_number,
                    'trailer_type': trailer.trailer_type
                } if trailer else None
            
            assignments_data.append({
                'id': assignment.id,
                'truck': truck_info,
                'trailer': trailer_info,
                'start_date': assignment.start_date.strftime('%Y-%m-%d'),
                'end_date': assignment.end_date.strftime('%Y-%m-%d') if assignment.end_date else None,
                'current': assignment.current
            })
        
        return jsonify({'assignments': assignments_data})
    
    except Exception as e:
        logger.error(f"Error fetching assignments: {e}")
        return jsonify({'error': 'Failed to fetch assignments'}), 500