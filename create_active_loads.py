"""
Script to create active loads for each driver with some at risk for pickup/delivery
Creates 2 loads per driver for this week (June 2-8, 2025)
"""

from datetime import datetime, timedelta
import random
from app import app, db
from models import Driver, Load, Client, Facility

def create_active_loads():
    with app.app_context():
        # Get all active drivers
        drivers = Driver.query.filter_by(status='active').all()
        print(f"Found {len(drivers)} active drivers")
        
        # Get existing clients and facilities
        clients = Client.query.all()
        facilities = Facility.query.all()
        
        if not clients or not facilities:
            print("No clients or facilities found. Creating some...")
            return
        
        # Define this week's date range (June 2-8, 2025)
        week_start = datetime(2025, 6, 2)
        week_end = datetime(2025, 6, 8, 23, 59, 59)
        current_time = datetime.utcnow()
        
        # Reference number counter
        ref_counter = 2025200
        
        # Create 2 loads per driver
        for driver in drivers:
            for load_num in range(2):
                ref_counter += 1
                
                # Random pickup and delivery facilities
                pickup_facility = random.choice(facilities)
                delivery_facility = random.choice([f for f in facilities if f.id != pickup_facility.id])
                client = random.choice(clients)
                
                # Schedule pickup time (randomly within this week)
                pickup_time = week_start + timedelta(
                    days=random.randint(0, 6),
                    hours=random.randint(6, 18),
                    minutes=random.choice([0, 15, 30, 45])
                )
                
                # Delivery time (4-12 hours after pickup)
                delivery_time = pickup_time + timedelta(
                    hours=random.randint(4, 12),
                    minutes=random.choice([0, 15, 30, 45])
                )
                
                # Determine status and risk factors
                status_options = ['scheduled', 'in_transit']
                status = random.choice(status_options)
                
                # Create some loads at risk
                at_risk = random.random() < 0.3  # 30% chance of being at risk
                
                actual_pickup_arrival = None
                actual_pickup_departure = None
                actual_delivery_arrival = None
                
                # If load is in transit, it has been picked up
                if status == 'in_transit':
                    if at_risk:
                        # Late pickup - arrived 15-60 minutes late
                        delay_minutes = random.randint(15, 60)
                        actual_pickup_arrival = pickup_time + timedelta(minutes=delay_minutes)
                        actual_pickup_departure = actual_pickup_arrival + timedelta(minutes=random.randint(15, 45))
                    else:
                        # On-time pickup
                        early_minutes = random.randint(-10, 10)  # Can be slightly early or late
                        actual_pickup_arrival = pickup_time + timedelta(minutes=early_minutes)
                        actual_pickup_departure = actual_pickup_arrival + timedelta(minutes=random.randint(15, 45))
                
                # For scheduled loads that are at risk, they might be late to even start
                if status == 'scheduled' and at_risk and pickup_time < current_time:
                    # This load should have been picked up already but hasn't
                    pass
                
                new_load = Load(
                    reference_number=f"REF-{ref_counter}",
                    client_id=client.id,
                    driver_id=driver.id,
                    pickup_facility_id=pickup_facility.id,
                    scheduled_pickup_time=pickup_time,
                    actual_pickup_arrival=actual_pickup_arrival,
                    actual_pickup_departure=actual_pickup_departure,
                    delivery_facility_id=delivery_facility.id,
                    scheduled_delivery_time=delivery_time,
                    actual_delivery_arrival=actual_delivery_arrival,
                    status=status,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(new_load)
                print(f"Created load {new_load.reference_number} for {driver.name} - {status}" + 
                      (" (AT RISK)" if at_risk else ""))
        
        db.session.commit()
        print(f"\nCreated {len(drivers) * 2} active loads for this week")
        
        # Print summary of at-risk loads
        at_risk_count = Load.query.filter(
            Load.status.in_(['scheduled', 'in_transit']),
            Load.actual_delivery_arrival == None,
            Load.scheduled_delivery_time >= week_start,
            Load.scheduled_delivery_time <= week_end
        ).count()
        print(f"Loads that might be at risk: {at_risk_count}")

if __name__ == "__main__":
    create_active_loads()