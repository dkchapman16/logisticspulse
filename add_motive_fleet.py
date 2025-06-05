#!/usr/bin/env python3
"""
Add Motive fleet data to existing database without removing test data
"""
import os
import sys
import requests
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Driver, Vehicle

API_KEY = os.getenv("MOTIVE_API_KEY")

def get_motive_users():
    """Get users from Motive API"""
    headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}
    response = requests.get("https://api.gomotive.com/v1/users", headers=headers)
    if response.status_code == 200:
        return response.json().get('users', [])
    return []

def get_motive_vehicles():
    """Get vehicles from Motive API"""
    headers = {"X-API-KEY": API_KEY, "Content-Type": "application/json"}
    response = requests.get("https://api.gomotive.com/v1/vehicles", headers=headers)
    if response.status_code == 200:
        return response.json().get('data', [])
    return []

def add_real_drivers():
    """Add real Motive drivers to database"""
    print("Adding Motive drivers...")
    users = get_motive_users()
    added = 0
    
    for user_item in users:
        user_data = user_item.get('user', {})
        
        # Only process active drivers (role=driver, status=active)
        if user_data.get('status') != 'active' or user_data.get('role') != 'driver':
            continue
            
        motive_id = str(user_data.get('id'))
        
        # Skip if already exists
        if Driver.query.filter_by(motive_driver_id=motive_id).first():
            continue
            
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        name = f"{first_name} {last_name}".strip()
        
        if not name:
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
        print(f"Added driver: {name}")
        added += 1
    
    return added

def add_real_vehicles():
    """Add real Motive vehicles to database"""
    print("Adding Motive vehicles...")
    vehicles = get_motive_vehicles()
    added = 0
    
    for vehicle_item in vehicles:
        vehicle_data = vehicle_item.get('vehicle', {})
        motive_id = str(vehicle_data.get('id'))
        
        # Skip if already exists
        if Vehicle.query.filter_by(motive_vehicle_id=motive_id).first():
            continue
            
        new_vehicle = Vehicle(
            motive_vehicle_id=motive_id,
            license_plate=vehicle_data.get('license_plate_number', ''),
            make=vehicle_data.get('make', ''),
            model=vehicle_data.get('model', ''),
            year=vehicle_data.get('year'),
            status='active' if vehicle_data.get('status') == 'active' else 'inactive'
        )
        db.session.add(new_vehicle)
        
        truck_name = f"{vehicle_data.get('make', '')} {vehicle_data.get('model', '')} #{vehicle_data.get('number', '')}"
        print(f"Added vehicle: {truck_name.strip()}")
        added += 1
    
    return added

if __name__ == "__main__":
    with app.app_context():
        try:
            print("Adding Motive fleet data to existing database...")
            
            drivers_added = add_real_drivers()
            vehicles_added = add_real_vehicles()
            
            db.session.commit()
            
            print(f"\nAdded to database:")
            print(f"  Real drivers: {drivers_added}")
            print(f"  Real vehicles: {vehicles_added}")
            
            # Show totals
            total_drivers = Driver.query.count()
            total_vehicles = Vehicle.query.count()
            print(f"\nTotal in database:")
            print(f"  Total drivers: {total_drivers}")
            print(f"  Total vehicles: {total_vehicles}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")