import logging
import math
from datetime import datetime
from app import db
from models import Load

logger = logging.getLogger(__name__)

def calculate_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the distance between two coordinates in miles
    
    Args:
        lat1 (float): Latitude of first point
        lng1 (float): Longitude of first point
        lat2 (float): Latitude of second point
        lng2 (float): Longitude of second point
    
    Returns:
        float: Distance in miles
    """
    # Earth's radius in miles
    radius = 3958.8
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlng = lng2_rad - lng1_rad
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = radius * c
    
    return distance

def is_in_geofence(lat, lng, fence_lat, fence_lng, radius):
    """
    Check if a point is inside a circular geofence
    
    Args:
        lat (float): Latitude of the point
        lng (float): Longitude of the point
        fence_lat (float): Latitude of the geofence center
        fence_lng (float): Longitude of the geofence center
        radius (float): Radius of the geofence in miles
    
    Returns:
        bool: True if point is inside geofence, False otherwise
    """
    distance = calculate_distance(lat, lng, fence_lat, fence_lng)
    return distance <= radius

def check_geofence_entry(load, current_lat, current_lng):
    """
    Check if a vehicle has entered or exited a facility geofence
    and update the load record if necessary
    
    Args:
        load (Load): The load object
        current_lat (float): Current latitude of the vehicle
        current_lng (float): Current longitude of the vehicle
    
    Returns:
        dict: Result of the check, including any status changes
    """
    status_changed = False
    entry_exit = None
    facility_type = None
    facility = None
    
    try:
        # Check pickup facility
        if load.pickup_facility and load.pickup_facility.lat and load.pickup_facility.lng:
            pickup_facility = load.pickup_facility
            in_pickup_geofence = is_in_geofence(
                current_lat, 
                current_lng, 
                pickup_facility.lat, 
                pickup_facility.lng, 
                pickup_facility.geofence_radius
            )
            
            # Check if arrived at pickup
            if in_pickup_geofence and not load.actual_pickup_arrival and load.status == 'scheduled':
                load.actual_pickup_arrival = datetime.utcnow()
                status_changed = True
                entry_exit = 'entry'
                facility_type = 'pickup'
                facility = pickup_facility
                logger.info(f"Vehicle entered pickup geofence for load {load.id}")
            
            # Check if departed from pickup
            elif not in_pickup_geofence and load.actual_pickup_arrival and not load.actual_pickup_departure:
                load.actual_pickup_departure = datetime.utcnow()
                load.status = 'in_transit'
                status_changed = True
                entry_exit = 'exit'
                facility_type = 'pickup'
                facility = pickup_facility
                logger.info(f"Vehicle exited pickup geofence for load {load.id}")
        
        # Check delivery facility
        if load.delivery_facility and load.delivery_facility.lat and load.delivery_facility.lng:
            delivery_facility = load.delivery_facility
            in_delivery_geofence = is_in_geofence(
                current_lat, 
                current_lng, 
                delivery_facility.lat, 
                delivery_facility.lng, 
                delivery_facility.geofence_radius
            )
            
            # Check if arrived at delivery
            if in_delivery_geofence and not load.actual_delivery_arrival and load.status == 'in_transit':
                load.actual_delivery_arrival = datetime.utcnow()
                status_changed = True
                entry_exit = 'entry'
                facility_type = 'delivery'
                facility = delivery_facility
                logger.info(f"Vehicle entered delivery geofence for load {load.id}")
            
            # Check if departed from delivery
            elif not in_delivery_geofence and load.actual_delivery_arrival and not load.actual_delivery_departure:
                load.actual_delivery_departure = datetime.utcnow()
                load.status = 'delivered'
                status_changed = True
                entry_exit = 'exit'
                facility_type = 'delivery'
                facility = delivery_facility
                logger.info(f"Vehicle exited delivery geofence for load {load.id}")
        
        # Compile results
        result = {
            'load_id': load.id,
            'status_changed': status_changed,
            'entry_exit': entry_exit,
            'facility_type': facility_type,
            'facility': {
                'id': facility.id,
                'name': facility.name
            } if facility else None
        }
        
        # If status changed, add the new load status to the result
        if status_changed:
            result['new_load_status'] = load.status
            
            # Update fields based on event type
            if entry_exit == 'entry' and facility_type == 'pickup':
                result['actual_pickup_arrival'] = load.actual_pickup_arrival.isoformat()
            elif entry_exit == 'exit' and facility_type == 'pickup':
                result['actual_pickup_departure'] = load.actual_pickup_departure.isoformat()
            elif entry_exit == 'entry' and facility_type == 'delivery':
                result['actual_delivery_arrival'] = load.actual_delivery_arrival.isoformat()
            elif entry_exit == 'exit' and facility_type == 'delivery':
                result['actual_delivery_departure'] = load.actual_delivery_departure.isoformat()
        
        return result
        
    except Exception as e:
        logger.error(f"Error in check_geofence_entry: {str(e)}")
        return {
            'error': str(e),
            'status_changed': False
        }
