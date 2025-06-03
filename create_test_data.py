#!/usr/bin/env python3
"""
Script to create test data for FreightPace logistics system
Creates 10 drivers, 10 vehicles, and 30 loads from May 2025
"""

import os
import sys
from datetime import datetime, timedelta
import random

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Driver, Vehicle, Client, Facility, Load, LocationUpdate, DriverPerformance

def create_test_data():
    with app.app_context():
        print("Creating test data...")
        
        # Clear existing data (optional - comment out if you want to keep existing data)
        print("Clearing existing data...")
        LocationUpdate.query.delete()
        Load.query.delete()
        DriverPerformance.query.delete()
        Facility.query.delete()
        Client.query.delete()
        Vehicle.query.delete()
        Driver.query.delete()
        db.session.commit()
        
        # Create 10 drivers
        print("Creating drivers...")
        drivers = []
        driver_names = [
            "John Smith", "Maria Garcia", "Robert Johnson", "Lisa Chen", 
            "David Wilson", "Sarah Davis", "Michael Brown", "Jennifer Lee",
            "Christopher Taylor", "Amanda Rodriguez"
        ]
        
        for i, name in enumerate(driver_names):
            driver = Driver(
                name=name,
                motive_driver_id=f"DRV{1000 + i}",
                phone=f"555-{1000 + i}",
                email=f"{name.lower().replace(' ', '.')}@company.com",
                status='active'
            )
            drivers.append(driver)
            db.session.add(driver)
        
        # Create 10 vehicles
        print("Creating vehicles...")
        vehicles = []
        vehicle_data = [
            ("ABC123", "Freightliner", "Cascadia", 2022),
            ("XYZ789", "Volvo", "VNL", 2021),
            ("DEF456", "Peterbilt", "579", 2023),
            ("GHI012", "Kenworth", "T680", 2022),
            ("JKL345", "Mack", "Anthem", 2021),
            ("MNO678", "International", "LT", 2020),
            ("PQR901", "Freightliner", "Cascadia", 2023),
            ("STU234", "Volvo", "VNL", 2022),
            ("VWX567", "Peterbilt", "389", 2021),
            ("YZA890", "Kenworth", "W990", 2023)
        ]
        
        for i, (plate, make, model, year) in enumerate(vehicle_data):
            vehicle = Vehicle(
                motive_vehicle_id=f"VEH{2000 + i}",
                license_plate=plate,
                make=make,
                model=model,
                year=year,
                status='active',
                current_lat=33.7490 + random.uniform(-2, 2),  # Around Atlanta
                current_lng=-84.3880 + random.uniform(-2, 2),
                last_updated=datetime.utcnow()
            )
            vehicles.append(vehicle)
            db.session.add(vehicle)
        
        # Create clients and commit first
        print("Creating clients...")
        clients = []
        client_names = [
            "Walmart Distribution", "Amazon Fulfillment", "Target Logistics",
            "Home Depot Supply", "FedEx Ground", "UPS Freight",
            "Nationwide Logistics", "American Transport", "Swift Transportation",
            "J.B. Hunt Transport"
        ]
        
        for name in client_names:
            client = Client(
                name=name,
                contact_name=f"Manager at {name}",
                contact_phone=f"555-{random.randint(1000, 9999)}",
                contact_email=f"contact@{name.lower().replace(' ', '')}.com"
            )
            clients.append(client)
            db.session.add(client)
        
        db.session.commit()  # Commit clients first to get their IDs
        
        # Create facilities
        print("Creating facilities...")
        facilities = []
        facility_data = [
            ("Atlanta Distribution Center", "1234 Industrial Blvd", "Atlanta", "GA", "30309", 33.7490, -84.3880),
            ("Charlotte Warehouse", "5678 Commerce St", "Charlotte", "NC", "28202", 35.2271, -80.8431),
            ("Nashville Depot", "9101 Freight Way", "Nashville", "TN", "37203", 36.1627, -86.7816),
            ("Memphis Hub", "1213 Logistics Dr", "Memphis", "TN", "38118", 35.1495, -90.0490),
            ("Birmingham Terminal", "1415 Transport Ave", "Birmingham", "AL", "35203", 33.5186, -86.8104),
            ("Jacksonville Port", "1617 Port Rd", "Jacksonville", "FL", "32226", 30.3322, -81.6557),
            ("Tampa Facility", "1819 Bay St", "Tampa", "FL", "33602", 27.9506, -82.4572),
            ("Savannah Logistics", "2021 River Dr", "Savannah", "GA", "31401", 32.0835, -81.0998),
            ("Columbia Center", "2223 Main St", "Columbia", "SC", "29201", 34.0007, -81.0348),
            ("Knoxville Yard", "2425 Mountain Rd", "Knoxville", "TN", "37902", 35.9606, -83.9207)
        ]
        
        for i, (name, address, city, state, zip_code, lat, lng) in enumerate(facility_data):
            facility = Facility(
                name=name,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                lat=lat,
                lng=lng,
                geofence_radius=0.3,  # 0.3 miles
                client_id=clients[i % len(clients)].id
            )
            facilities.append(facility)
            db.session.add(facility)
        
        db.session.commit()
        
        # Create 30 loads from May 2025
        print("Creating loads...")
        loads = []
        may_start = datetime(2025, 5, 1)
        may_end = datetime(2025, 5, 31)
        
        for i in range(30):
            # Random date in May 2025
            random_days = random.randint(0, 30)
            load_date = may_start + timedelta(days=random_days)
            
            # Random pickup and delivery times
            pickup_time = load_date + timedelta(hours=random.randint(6, 18))
            delivery_time = pickup_time + timedelta(hours=random.randint(4, 24))
            
            # Select random facilities for pickup and delivery
            pickup_facility = random.choice(facilities)
            delivery_facility = random.choice([f for f in facilities if f.id != pickup_facility.id])
            
            # Create load
            load = Load(
                reference_number=f"{610000 + i}",
                client_id=random.choice(clients).id,
                driver_id=drivers[i % len(drivers)].id,
                vehicle_id=vehicles[i % len(vehicles)].id,
                pickup_facility_id=pickup_facility.id,
                scheduled_pickup_time=pickup_time,
                delivery_facility_id=delivery_facility.id,
                scheduled_delivery_time=delivery_time,
                status='delivered',  # All loads are completed (in the past)
                created_at=load_date
            )
            
            # Simulate on-time vs late performance (70% on time, 30% late)
            pickup_on_time = random.random() < 0.7
            delivery_on_time = random.random() < 0.7
            
            if pickup_on_time:
                # On time pickup (within 30 minutes of scheduled)
                actual_pickup_arrival = pickup_time + timedelta(minutes=random.randint(-15, 30))
                actual_pickup_departure = actual_pickup_arrival + timedelta(minutes=random.randint(15, 45))
            else:
                # Late pickup (30 minutes to 3 hours late)
                actual_pickup_arrival = pickup_time + timedelta(minutes=random.randint(30, 180))
                actual_pickup_departure = actual_pickup_arrival + timedelta(minutes=random.randint(15, 45))
            
            if delivery_on_time:
                # On time delivery
                actual_delivery_arrival = delivery_time + timedelta(minutes=random.randint(-15, 30))
                actual_delivery_departure = actual_delivery_arrival + timedelta(minutes=random.randint(15, 30))
            else:
                # Late delivery
                actual_delivery_arrival = delivery_time + timedelta(minutes=random.randint(30, 240))
                actual_delivery_departure = actual_delivery_arrival + timedelta(minutes=random.randint(15, 30))
            
            load.actual_pickup_arrival = actual_pickup_arrival
            load.actual_pickup_departure = actual_pickup_departure
            load.actual_delivery_arrival = actual_delivery_arrival
            load.actual_delivery_departure = actual_delivery_departure
            
            loads.append(load)
            db.session.add(load)
        
        db.session.commit()
        
        # Create driver performance records
        print("Creating driver performance records...")
        for driver in drivers:
            driver_loads = [load for load in loads if load.driver_id == driver.id]
            
            # Group loads by date
            performance_by_date = {}
            for load in driver_loads:
                date = load.scheduled_pickup_time.date()
                if date not in performance_by_date:
                    performance_by_date[date] = {
                        'loads_completed': 0,
                        'on_time_pickups': 0,
                        'on_time_deliveries': 0,
                        'total_delay_minutes': 0
                    }
                
                perf = performance_by_date[date]
                perf['loads_completed'] += 1
                
                if load.pickup_on_time():
                    perf['on_time_pickups'] += 1
                else:
                    delay = (load.actual_pickup_arrival - load.scheduled_pickup_time).total_seconds() / 60
                    perf['total_delay_minutes'] += max(0, delay)
                
                if load.delivery_on_time():
                    perf['on_time_deliveries'] += 1
                else:
                    delay = (load.actual_delivery_arrival - load.scheduled_delivery_time).total_seconds() / 60
                    perf['total_delay_minutes'] += max(0, delay)
            
            # Create performance records
            for date, perf in performance_by_date.items():
                avg_delay = perf['total_delay_minutes'] / perf['loads_completed'] if perf['loads_completed'] > 0 else 0
                
                driver_perf = DriverPerformance(
                    driver_id=driver.id,
                    date=date,
                    loads_completed=perf['loads_completed'],
                    on_time_pickups=perf['on_time_pickups'],
                    on_time_deliveries=perf['on_time_deliveries'],
                    average_delay_minutes=avg_delay
                )
                db.session.add(driver_perf)
        
        db.session.commit()
        
        print(f"Successfully created:")
        print(f"- {len(drivers)} drivers")
        print(f"- {len(vehicles)} vehicles")
        print(f"- {len(clients)} clients")
        print(f"- {len(facilities)} facilities")
        print(f"- {len(loads)} loads")
        print(f"- Driver performance records for May 2025")
        print("Test data creation complete!")

if __name__ == "__main__":
    create_test_data()