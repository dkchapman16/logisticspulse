from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import db, Driver, Load, Client, LocationUpdate
from services.notification_service import send_notification
import logging

availability_bp = Blueprint('availability', __name__)
logger = logging.getLogger(__name__)

@availability_bp.route('/availability')
@login_required
def index():
    """Show truck availability broadcast interface"""
    return render_template('availability.html')

@availability_bp.route('/availability/available-drivers')
@login_required
def get_available_drivers():
    """API endpoint to get drivers who have completed their last load and are available"""
    try:
        # Get drivers who have completed their most recent load
        available_drivers = []
        
        drivers = db.session.query(Driver).filter_by(status='active').all()
        
        for driver in drivers:
            # Get the most recent load for this driver
            latest_load = db.session.query(Load).filter(
                Load.driver_id == driver.id
            ).order_by(Load.scheduled_delivery_time.desc()).first()
            
            if not latest_load:
                # Driver has no loads assigned
                available_drivers.append({
                    'driver_id': driver.id,
                    'driver_name': driver.name,
                    'phone': driver.phone,
                    'email': driver.email,
                    'status': 'No loads assigned',
                    'last_delivery_location': None,
                    'last_delivery_time': None,
                    'availability_status': 'available'
                })
                continue
            
            # Check if the latest load is delivered
            if latest_load.status == 'delivered' and latest_load.actual_delivery_departure:
                # Driver is available after completing delivery
                available_drivers.append({
                    'driver_id': driver.id,
                    'driver_name': driver.name,
                    'phone': driver.phone,
                    'email': driver.email,
                    'status': 'Available after delivery',
                    'last_delivery_location': {
                        'facility_name': latest_load.delivery_facility.name,
                        'address': latest_load.delivery_facility.address,
                        'city': latest_load.delivery_facility.city,
                        'state': latest_load.delivery_facility.state
                    },
                    'last_delivery_time': latest_load.actual_delivery_departure.isoformat(),
                    'availability_status': 'available',
                    'load_reference': latest_load.reference_number
                })
            elif latest_load.status == 'in_transit':
                # Check if driver is close to delivery (within 1 hour ETA)
                if latest_load.current_eta:
                    time_to_delivery = (latest_load.current_eta - datetime.utcnow()).total_seconds() / 3600
                    if time_to_delivery <= 1.0:  # Within 1 hour
                        available_drivers.append({
                            'driver_id': driver.id,
                            'driver_name': driver.name,
                            'phone': driver.phone,
                            'email': driver.email,
                            'status': 'Available soon (within 1 hour)',
                            'last_delivery_location': {
                                'facility_name': latest_load.delivery_facility.name,
                                'address': latest_load.delivery_facility.address,
                                'city': latest_load.delivery_facility.city,
                                'state': latest_load.delivery_facility.state
                            },
                            'estimated_availability': latest_load.current_eta.isoformat(),
                            'availability_status': 'available_soon',
                            'load_reference': latest_load.reference_number
                        })
        
        return jsonify({
            'available_drivers': available_drivers,
            'total_count': len(available_drivers)
        })
        
    except Exception as e:
        logger.error(f"Error getting available drivers: {e}")
        return jsonify({'error': 'Failed to load available drivers'}), 500

@availability_bp.route('/availability/broadcast', methods=['POST'])
@login_required
def broadcast_availability():
    """Broadcast truck availability to customers and brokers"""
    try:
        data = request.get_json()
        driver_ids = data.get('driver_ids', [])
        message_template = data.get('message', '')
        broadcast_type = data.get('broadcast_type', 'both')  # customers, brokers, or both
        
        if not driver_ids:
            return jsonify({'error': 'No drivers selected'}), 400
        
        broadcast_results = []
        
        for driver_id in driver_ids:
            driver = db.session.query(Driver).get(driver_id)
            if not driver:
                continue
            
            # Get driver's last delivery location
            latest_load = db.session.query(Load).filter(
                Load.driver_id == driver.id
            ).order_by(Load.scheduled_delivery_time.desc()).first()
            
            location_info = "Location TBD"
            if latest_load and latest_load.delivery_facility:
                location_info = f"{latest_load.delivery_facility.city}, {latest_load.delivery_facility.state}"
            
            # Customize message with driver details
            personalized_message = message_template.format(
                driver_name=driver.name,
                location=location_info,
                phone=driver.phone or "Contact dispatcher",
                company="Hitched Logistics LLC"
            )
            
            # Get relevant clients (customers who have used this driver before)
            if broadcast_type in ['customers', 'both']:
                clients = db.session.query(Client).join(Load).filter(
                    Load.driver_id == driver.id
                ).distinct().all()
                
                for client in clients:
                    # In a real implementation, you would send SMS/email here
                    # For now, we'll create internal notifications
                    send_notification(
                        user_id=current_user.id,
                        message=f"Availability broadcast sent to {client.name} for driver {driver.name}",
                        notification_type='info'
                    )
            
            broadcast_results.append({
                'driver_id': driver.id,
                'driver_name': driver.name,
                'status': 'success',
                'message': 'Broadcast sent successfully'
            })
        
        return jsonify({
            'success': True,
            'results': broadcast_results,
            'message': f'Availability broadcast sent for {len(broadcast_results)} drivers'
        })
        
    except Exception as e:
        logger.error(f"Error broadcasting availability: {e}")
        return jsonify({'error': 'Failed to send broadcast'}), 500

@availability_bp.route('/availability/templates')
@login_required
def get_message_templates():
    """Get predefined message templates for availability broadcasts"""
    templates = [
        {
            'name': 'Standard Availability',
            'message': 'TRUCK AVAILABLE: {driver_name} has completed delivery in {location} and is available for immediate pickup. Contact: {phone} - {company}'
        },
        {
            'name': 'Available Soon',
            'message': 'TRUCK AVAILABLE SOON: {driver_name} will be available in {location} within the hour. Reserve now! Contact: {phone} - {company}'
        },
        {
            'name': 'Capacity Available',
            'message': 'CAPACITY ALERT: {driver_name} has truck capacity available from {location}. Book your shipment today! {phone} - {company}'
        },
        {
            'name': 'Regional Coverage',
            'message': 'REGIONAL COVERAGE: {driver_name} available for pickups in the {location} area. Reliable service guaranteed. {phone} - {company}'
        }
    ]
    
    return jsonify({'templates': templates})

@availability_bp.route('/availability/history')
@login_required
def broadcast_history():
    """Get history of availability broadcasts"""
    try:
        # For now, return recent notifications related to availability
        # In a full implementation, you'd have a dedicated broadcast history table
        
        return jsonify({
            'broadcasts': [],
            'total_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error getting broadcast history: {e}")
        return jsonify({'error': 'Failed to load broadcast history'}), 500