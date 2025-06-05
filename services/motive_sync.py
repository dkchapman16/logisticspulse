import os
from datetime import datetime
from .motive_api_key import get_drivers, get_vehicles
from .logger import setup_logger
from models import Driver, Vehicle, db

logger = setup_logger(__name__)

def sync_drivers_from_motive():
    """Sync drivers from Motive API to database"""
    motive_drivers = get_drivers()
    if not motive_drivers:
        logger.warning("No drivers returned from Motive API")
        return 0
    
    synced_count = 0
    for motive_driver in motive_drivers:
        user_data = motive_driver.get('user', {})
        
        # Extract driver information
        motive_id = str(user_data.get('id'))
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        name = f"{first_name} {last_name}".strip()
        email = user_data.get('email', '')
        phone = user_data.get('phone', '')
        status = 'active' if user_data.get('status') == 'active' else 'inactive'
        
        if not name or not motive_id:
            continue
            
        # Check if driver already exists
        existing_driver = Driver.query.filter_by(motive_driver_id=motive_id).first()
        
        if existing_driver:
            # Update existing driver
            existing_driver.name = name
            existing_driver.email = email
            existing_driver.phone = phone
            existing_driver.status = status
            logger.info(f"Updated driver: {name}")
        else:
            # Create new driver
            new_driver = Driver(
                name=name,
                motive_driver_id=motive_id,
                email=email,
                phone=phone,
                company='Hitched Logistics LLC',
                status=status
            )
            db.session.add(new_driver)
            logger.info(f"Added new driver: {name}")
        
        synced_count += 1
    
    try:
        db.session.commit()
        logger.info(f"Successfully synced {synced_count} drivers from Motive")
        return synced_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing drivers: {e}")
        return 0

def sync_vehicles_from_motive():
    """Sync vehicles from Motive API to database"""
    motive_vehicles = get_vehicles()
    if not motive_vehicles:
        logger.warning("No vehicles returned from Motive API")
        return 0
    
    synced_count = 0
    for motive_vehicle in motive_vehicles:
        vehicle_data = motive_vehicle.get('vehicle', {})
        
        # Extract vehicle information
        motive_id = str(vehicle_data.get('id'))
        number = vehicle_data.get('number', '')
        license_plate = vehicle_data.get('license_plate_number', '')
        make = vehicle_data.get('make', '')
        model = vehicle_data.get('model', '')
        year = vehicle_data.get('year')
        status = 'active' if vehicle_data.get('status') == 'active' else 'inactive'
        
        if not motive_id:
            continue
            
        # Check if vehicle already exists
        existing_vehicle = Vehicle.query.filter_by(motive_vehicle_id=motive_id).first()
        
        if existing_vehicle:
            # Update existing vehicle
            existing_vehicle.license_plate = license_plate
            existing_vehicle.make = make
            existing_vehicle.model = model
            existing_vehicle.year = year
            existing_vehicle.status = status
            logger.info(f"Updated vehicle: {number or license_plate}")
        else:
            # Create new vehicle
            new_vehicle = Vehicle(
                motive_vehicle_id=motive_id,
                license_plate=license_plate,
                make=make,
                model=model,
                year=year,
                status=status
            )
            db.session.add(new_vehicle)
            logger.info(f"Added new vehicle: {number or license_plate}")
        
        synced_count += 1
    
    try:
        db.session.commit()
        logger.info(f"Successfully synced {synced_count} vehicles from Motive")
        return synced_count
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing vehicles: {e}")
        return 0

def sync_all_from_motive():
    """Sync both drivers and vehicles from Motive"""
    logger.info("Starting full sync from Motive API")
    
    drivers_synced = sync_drivers_from_motive()
    vehicles_synced = sync_vehicles_from_motive()
    
    return {
        'drivers_synced': drivers_synced,
        'vehicles_synced': vehicles_synced,
        'total_synced': drivers_synced + vehicles_synced
    }