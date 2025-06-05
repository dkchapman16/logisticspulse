#!/usr/bin/env python3
"""
Standalone script to sync Motive fleet data to database
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
BASE_URL = "https://api.gomotive.com/v1"

def get_motive_data(endpoint):
    """Get data from Motive API"""
    if not API_KEY:
        print("MOTIVE_API_KEY not found")
        return []
    
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", headers=headers)
        if response.status_code == 200:
            data = response.json()
            return data.get('data', data.get(endpoint, data.get('users', [])))
        else:
            print(f"API error for {endpoint}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return []

def sync_drivers():
    """Sync drivers from Motive"""
    print("Syncing drivers from Motive...")
    motive_users = get_motive_data('users')
    
    synced = 0
    for user_item in motive_users:
        user_data = user_item.get('user', {})
        
        motive_id = str(user_data.get('id'))
        first_name = user_data.get('first_name', '').strip()
        last_name = user_data.get('last_name', '').strip()
        name = f"{first_name} {last_name}".strip()
        email = user_data.get('email', '')
        phone = user_data.get('phone', '')
        status = 'active' if user_data.get('status') == 'active' else 'inactive'
        
        if not name or not motive_id:
            continue
            
        # Check if driver exists
        existing = Driver.query.filter_by(motive_driver_id=motive_id).first()
        
        if existing:
            existing.name = name
            existing.email = email
            existing.phone = phone
            existing.status = status
            print(f"Updated: {name}")
        else:
            new_driver = Driver(
                name=name,
                motive_driver_id=motive_id,
                email=email,
                phone=phone,
                company='Hitched Logistics LLC',
                status=status
            )
            db.session.add(new_driver)
            print(f"Added: {name}")
        
        synced += 1
    
    return synced

def sync_vehicles():
    """Sync vehicles from Motive"""
    print("Syncing vehicles from Motive...")
    motive_vehicles = get_motive_data('vehicles')
    
    synced = 0
    for vehicle_item in motive_vehicles:
        vehicle_data = vehicle_item.get('vehicle', {})
        
        motive_id = str(vehicle_data.get('id'))
        number = vehicle_data.get('number', '')
        license_plate = vehicle_data.get('license_plate_number', '')
        make = vehicle_data.get('make', '')
        model = vehicle_data.get('model', '')
        year = vehicle_data.get('year')
        status = 'active' if vehicle_data.get('status') == 'active' else 'inactive'
        
        if not motive_id:
            continue
            
        # Check if vehicle exists
        existing = Vehicle.query.filter_by(motive_vehicle_id=motive_id).first()
        
        vehicle_name = f"{make} {model} #{number}" if number else f"{make} {model}"
        
        if existing:
            existing.license_plate = license_plate
            existing.make = make
            existing.model = model
            existing.year = year
            existing.status = status
            print(f"Updated: {vehicle_name}")
        else:
            new_vehicle = Vehicle(
                motive_vehicle_id=motive_id,
                license_plate=license_plate,
                make=make,
                model=model,
                year=year,
                status=status
            )
            db.session.add(new_vehicle)
            print(f"Added: {vehicle_name}")
        
        synced += 1
    
    return synced

if __name__ == "__main__":
    with app.app_context():
        try:
            print("Starting Motive data sync...")
            
            drivers_synced = sync_drivers()
            vehicles_synced = sync_vehicles()
            
            db.session.commit()
            
            print(f"\n✅ Sync completed:")
            print(f"   Drivers synced: {drivers_synced}")
            print(f"   Vehicles synced: {vehicles_synced}")
            print(f"   Total: {drivers_synced + vehicles_synced}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Sync failed: {e}")