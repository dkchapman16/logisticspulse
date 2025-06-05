from datetime import datetime, timedelta
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='dispatcher')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Driver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    motive_driver_id = db.Column(db.String(100), unique=True)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    company = db.Column(db.String(200), default='Hitched Logistics LLC')
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    loads = db.relationship('Load', backref='driver', lazy=True)
    performance_records = db.relationship('DriverPerformance', backref='driver', lazy=True)
    
    def on_time_percentage(self, period=30):
        """Calculate on-time percentage over the given period (in days)"""
        # Implementation will be added in service layer
        pass

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    motive_vehicle_id = db.Column(db.String(100), unique=True)
    license_plate = db.Column(db.String(20))
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    year = db.Column(db.Integer)
    status = db.Column(db.String(20), default='active')
    current_lat = db.Column(db.Float)
    current_lng = db.Column(db.Float)
    last_updated = db.Column(db.DateTime)
    
    # Relationships
    loads = db.relationship('Load', backref='vehicle', lazy=True)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100))
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    facilities = db.relationship('Facility', backref='client', lazy=True)
    loads = db.relationship('Load', backref='client', lazy=True)

class Facility(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(20))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    geofence_radius = db.Column(db.Float, default=0.2)  # in miles
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pickups = db.relationship('Load', foreign_keys='Load.pickup_facility_id', backref='pickup_facility', lazy=True)
    deliveries = db.relationship('Load', foreign_keys='Load.delivery_facility_id', backref='delivery_facility', lazy=True)

class Load(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True)
    ratecon_url = db.Column(db.String(200))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    
    # Pickup details
    pickup_facility_id = db.Column(db.Integer, db.ForeignKey('facility.id'), nullable=False)
    scheduled_pickup_time = db.Column(db.DateTime, nullable=False)
    actual_pickup_arrival = db.Column(db.DateTime)
    actual_pickup_departure = db.Column(db.DateTime)
    
    # Delivery details
    delivery_facility_id = db.Column(db.Integer, db.ForeignKey('facility.id'), nullable=False)
    scheduled_delivery_time = db.Column(db.DateTime, nullable=False)
    actual_delivery_arrival = db.Column(db.DateTime)
    actual_delivery_departure = db.Column(db.DateTime)
    
    # ETA and status
    current_eta = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, in_transit, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    location_updates = db.relationship('LocationUpdate', backref='load', lazy=True)
    
    @property
    def pickup_on_time(self):
        if not self.actual_pickup_arrival or not self.scheduled_pickup_time:
            return None
        # Strict on-time: must be on scheduled time or earlier
        return self.actual_pickup_arrival <= self.scheduled_pickup_time
    
    @property
    def delivery_on_time(self):
        if not self.actual_delivery_arrival or not self.scheduled_delivery_time:
            return None
        # Strict on-time: must be on scheduled time or earlier
        return self.actual_delivery_arrival <= self.scheduled_delivery_time

class LocationUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    load_id = db.Column(db.Integer, db.ForeignKey('load.id'), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    speed = db.Column(db.Float)  # mph
    heading = db.Column(db.Float)  # degrees
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class DriverPerformance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    loads_completed = db.Column(db.Integer, default=0)
    on_time_pickups = db.Column(db.Integer, default=0)
    on_time_deliveries = db.Column(db.Integer, default=0)
    average_delay_minutes = db.Column(db.Float, default=0)
    
    @property
    def on_time_pickup_percentage(self):
        if self.loads_completed == 0:
            return 0
        return (self.on_time_pickups / self.loads_completed) * 100
    
    @property
    def on_time_delivery_percentage(self):
        if self.loads_completed == 0:
            return 0
        return (self.on_time_deliveries / self.loads_completed) * 100

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    load_id = db.Column(db.Integer, db.ForeignKey('load.id'))
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'))
    type = db.Column(db.String(50))  # 'late_risk', 'on_time', 'late', etc.
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    load = db.relationship('Load', backref='notifications')
    driver = db.relationship('Driver', backref='notifications')

class Milestone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    type = db.Column(db.String(50))  # 'consecutive_on_time', 'monthly_perfect', etc.
    value = db.Column(db.Integer)
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='milestones')


class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    truck_number = db.Column(db.String(50), unique=True, nullable=False)
    vin = db.Column(db.String(17), unique=True)
    year = db.Column(db.Integer)
    make = db.Column(db.String(50))
    model = db.Column(db.String(50))
    color = db.Column(db.String(30))
    license_plate = db.Column(db.String(20))
    state = db.Column(db.String(2))
    status = db.Column(db.String(20), default='active')  # active, inactive, maintenance
    
    # Expiration dates
    dot_expiration = db.Column(db.Date)
    annual_inspection_expiration = db.Column(db.Date)
    insurance_expiration = db.Column(db.Date)
    registration_expiration = db.Column(db.Date)
    annual_permit_expiration = db.Column(db.Date)
    or_permit_expiration = db.Column(db.Date)
    monthly_inspection = db.Column(db.Date)
    
    # Company IFTA
    ifta_decal = db.Column(db.String(50))
    
    # Finance
    ownership_type = db.Column(db.String(20))  # owned, leased, rental
    date_acquired = db.Column(db.Date)
    payment_start_date = db.Column(db.Date)
    payment_amount = db.Column(db.Float)
    monthly_payment = db.Column(db.Boolean, default=False)
    service_date = db.Column(db.Date)
    lender = db.Column(db.String(100))
    contract_number = db.Column(db.String(50))
    date_sold = db.Column(db.Date)
    
    # Specs
    sleeper_purchased = db.Column(db.Boolean, default=False)
    engine_type_brand = db.Column(db.String(50))
    brake_type_brand = db.Column(db.String(50))
    empty_weight = db.Column(db.Integer)
    current_value = db.Column(db.Float)
    replacement_cost = db.Column(db.Float)
    
    # Notes
    notes = db.Column(db.Text)
    
    # Fuel card
    fuel_card = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Trailer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trailer_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, maintenance
    labels = db.Column(db.String(200))
    trailer_type = db.Column(db.String(50))  # dry_van, flatbed, reefer, etc.
    length = db.Column(db.Integer)
    model = db.Column(db.String(50))
    vin = db.Column(db.String(17))
    width = db.Column(db.Integer)
    brake_type = db.Column(db.String(50))
    roof = db.Column(db.String(50))
    state = db.Column(db.String(2))
    license_plate = db.Column(db.String(20))
    
    # Expiration dates
    annual_inspection_expiration = db.Column(db.Date)
    insurance_expiration = db.Column(db.Date)
    registration_expiration = db.Column(db.Date)
    annual_permit_expiration = db.Column(db.Date)
    or_permit_expiration = db.Column(db.Date)
    monthly_inspection = db.Column(db.Date)
    
    # Finance
    ownership_type = db.Column(db.String(20))  # owned, leased, rental
    other_accounts = db.Column(db.String(100))
    payment_start_date = db.Column(db.Date)
    payment_amount = db.Column(db.Float)
    monthly_payment = db.Column(db.Boolean, default=False)
    service_date = db.Column(db.Date)
    lender = db.Column(db.String(100))
    contract_number = db.Column(db.String(50))
    date_sold = db.Column(db.Date)
    
    # Features
    freight_walls = db.Column(db.Boolean, default=False)
    winches = db.Column(db.Boolean, default=False)
    ramps = db.Column(db.Boolean, default=False)
    recessed_dte = db.Column(db.Boolean, default=False)
    other = db.Column(db.String(100))
    
    # Notes
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssetAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    truck_id = db.Column(db.Integer, db.ForeignKey('truck.id'))
    trailer_id = db.Column(db.Integer, db.ForeignKey('trailer.id'))
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    current = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    driver = db.relationship('Driver', backref='asset_assignments')
    truck = db.relationship('Truck', backref='assignments')
    trailer = db.relationship('Trailer', backref='assignments')
