
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from models import Load, Client, Facility, Driver
from datetime import datetime

loads_bp = Blueprint('loads', __name__)

@loads_bp.route('/loads/create', methods=['GET', 'POST'])
def create_load():
    if request.method == 'POST':
        data = request.form

        # Lookup or create client
        client_name = data.get('client_name')
        client = Client.query.filter_by(name=client_name).first()
        if not client:
            client = Client(name=client_name)
            db.session.add(client)
            db.session.commit()

        # Lookup or create pickup facility
        pickup_address = data.get('pickup_address')
        pickup_name = data.get('pickup_name')
        pickup_facility = Facility.query.filter_by(address=pickup_address).first()
        if not pickup_facility:
            pickup_facility = Facility(name=pickup_name, address=pickup_address)
            db.session.add(pickup_facility)
            db.session.commit()

        # Lookup or create delivery facility
        delivery_address = data.get('delivery_address')
        delivery_name = data.get('delivery_name')
        delivery_facility = Facility.query.filter_by(address=delivery_address).first()
        if not delivery_facility:
            delivery_facility = Facility(name=delivery_name, address=delivery_address)
            db.session.add(delivery_facility)
            db.session.commit()

        load = Load(
            reference_number=data.get('reference_number'),
            pickup_facility_id=pickup_facility.id,
            delivery_facility_id=delivery_facility.id,
            scheduled_pickup_time=datetime.fromisoformat(data.get('pickup_time')),
            scheduled_delivery_time=datetime.fromisoformat(data.get('delivery_time')),
            client_id=client.id,
            driver_id=data.get('driver_id')
        )
        db.session.add(load)
        db.session.commit()

        flash('Load created successfully!', 'success')
        return redirect(url_for('loads.index'))

    # Example data context; in practice, ensure 'data' is provided from RateCon extraction flow
    # data = {'reference_number': '', 'pickup': {}, 'delivery': {}, 'client': {}}
    drivers = Driver.query.all()
    return render_template('create_load.html', drivers=drivers, data={})
