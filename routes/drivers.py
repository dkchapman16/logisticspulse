from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import Driver, DriverPerformance, Load, Milestone
from services.motive_api import get_active_driver_locations
from services.google_maps_api import get_eta
import logging

logger = logging.getLogger(__name__)
drivers_bp = Blueprint('drivers', __name__)

@drivers_bp.route('/drivers')
def index():
    """Show all drivers"""
    return render_template('drivers.html')

@drivers_bp.route('/drivers/data')
def get_drivers():
    """API endpoint to get all drivers with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    status_filter = request.args.get('status', None)
    
    query = Driver.query
    
    # Apply filters
    if status_filter:
        query = query.filter(Driver.status == status_filter)
    
    # Sort active drivers before inactive ones, then by name
    query = query.order_by(
        db.case(
            (Driver.status == 'active', 0),
            else_=1
        ),
        Driver.name.asc()
    )
    
    # Paginate results
    drivers_page = query.paginate(page=page, per_page=per_page)
    
    # Format response data - use May 2025 test data period
    today = datetime(2025, 5, 31).date()
    month_ago = datetime(2025, 5, 1).date()
    
    drivers_data = []
    for driver in drivers_page.items:
        # Get loads directly from the Load table for accurate count
        month_ago_datetime = datetime.combine(month_ago, datetime.min.time())
        loads = Load.query.filter(
            Load.driver_id == driver.id,
            Load.scheduled_pickup_time >= month_ago_datetime
        ).all()
        
        total_loads = len(loads)
        on_time_pickups = sum(1 for load in loads if load.pickup_on_time == True)
        on_time_deliveries = sum(1 for load in loads if load.delivery_on_time == True)
        
        pickup_percentage = (on_time_pickups / total_loads * 100) if total_loads > 0 else 0
        delivery_percentage = (on_time_deliveries / total_loads * 100) if total_loads > 0 else 0
        
        # Get active load
        active_load = Load.query.filter(
            Load.driver_id == driver.id,
            Load.status.in_(['scheduled', 'in_transit'])
        ).order_by(Load.scheduled_delivery_time).first()
        
        drivers_data.append({
            'id': driver.id,
            'name': driver.name,
            'phone': driver.phone,
            'email': driver.email,
            'status': driver.status,
            'motive_id': driver.motive_driver_id,
            'total_loads': total_loads,
            'on_time_pickup_percentage': round(pickup_percentage, 1),
            'on_time_delivery_percentage': round(delivery_percentage, 1),
            'active_load': {
                'id': active_load.id,
                'reference': active_load.reference_number,
                'status': active_load.status,
                'eta': active_load.current_eta.strftime('%Y-%m-%d %H:%M') if active_load.current_eta else None
            } if active_load else None
        })
    
    return jsonify({
        'drivers': drivers_data,
        'page': page,
        'per_page': per_page,
        'total': drivers_page.total,
        'pages': drivers_page.pages
    })

@drivers_bp.route('/drivers/<int:driver_id>')
def driver_detail(driver_id):
    """Show driver details and performance"""
    driver = Driver.query.get_or_404(driver_id)
    return render_template('driver_detail.html', driver=driver)

@drivers_bp.route('/drivers/<int:driver_id>/data')
def get_driver_data(driver_id):
    """API endpoint to get detailed driver performance data"""
    driver = Driver.query.get_or_404(driver_id)
    
    # Get time ranges
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Get recent loads (completed in the last 30 days or upcoming)
    completed_loads = Load.query.filter(
        Load.driver_id == driver.id,
        Load.status.in_(['delivered']),
        Load.actual_delivery_arrival >= datetime.combine(month_ago, datetime.min.time())
    ).order_by(Load.actual_delivery_arrival.desc()).limit(10).all()
    
    upcoming_loads = Load.query.filter(
        Load.driver_id == driver.id,
        Load.status.in_(['scheduled', 'in_transit'])
    ).order_by(Load.scheduled_delivery_time).limit(5).all()
    
    # Format load data
    completed_loads_data = [{
        'id': load.id,
        'reference': load.reference_number,
        'pickup': load.pickup_facility.name if load.pickup_facility else 'Unknown',
        'delivery': load.delivery_facility.name if load.delivery_facility else 'Unknown',
        'scheduled_pickup': load.scheduled_pickup_time.strftime('%Y-%m-%d %H:%M') if load.scheduled_pickup_time else None,
        'actual_pickup': load.actual_pickup_arrival.strftime('%Y-%m-%d %H:%M') if load.actual_pickup_arrival else None,
        'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
        'actual_delivery': load.actual_delivery_arrival.strftime('%Y-%m-%d %H:%M') if load.actual_delivery_arrival else None,
        'on_time': load.pickup_on_time == True and load.delivery_on_time == True
    } for load in completed_loads]
    
    upcoming_loads_data = [{
        'id': load.id,
        'reference': load.reference_number,
        'pickup': load.pickup_facility.name if load.pickup_facility else 'Unknown',
        'delivery': load.delivery_facility.name if load.delivery_facility else 'Unknown',
        'scheduled_pickup': load.scheduled_pickup_time.strftime('%Y-%m-%d %H:%M'),
        'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
        'status': load.status,
        'current_eta': load.current_eta.strftime('%Y-%m-%d %H:%M') if load.current_eta else None
    } for load in upcoming_loads]
    
    # Calculate performance directly from Load data instead of DriverPerformance records
    # Use May 2025 test data period
    today = datetime(2025, 5, 31).date()
    yesterday = datetime(2025, 5, 30).date()
    week_ago = datetime(2025, 5, 24).date()
    month_ago = datetime(2025, 5, 1).date()
    
    month_ago_datetime = datetime.combine(month_ago, datetime.min.time())
    
    # Get all loads for this driver in the period
    all_loads = Load.query.filter(
        Load.driver_id == driver.id,
        Load.scheduled_pickup_time >= month_ago_datetime
    ).all()
    
    # Filter loads by periods
    today_loads = [l for l in all_loads if l.scheduled_pickup_time.date() == today]
    yesterday_loads = [l for l in all_loads if l.scheduled_pickup_time.date() == yesterday]
    weekly_loads = [l for l in all_loads if l.scheduled_pickup_time.date() >= week_ago]
    monthly_loads = all_loads
    
    # Helper function to calculate metrics for a load set
    def calculate_metrics(loads):
        if not loads:
            return {
                'loads': 0,
                'on_time_loads': 0,
                'on_time_percentage': 0,
                'avg_delay': 0
            }
        
        total_loads = len(loads)
        
        # A load is considered on-time only if BOTH pickup AND delivery are on-time
        on_time_loads = sum(1 for load in loads 
                           if load.pickup_on_time == True and load.delivery_on_time == True)
        
        # Calculate average delay for late loads
        total_delay = 0
        delay_count = 0
        for load in loads:
            # Check pickup delay
            if load.actual_pickup_arrival and load.scheduled_pickup_time:
                delay = (load.actual_pickup_arrival - load.scheduled_pickup_time).total_seconds() / 60
                if delay > 0:
                    total_delay += delay
                    delay_count += 1
            
            # Check delivery delay  
            if load.actual_delivery_arrival and load.scheduled_delivery_time:
                delay = (load.actual_delivery_arrival - load.scheduled_delivery_time).total_seconds() / 60
                if delay > 0:
                    total_delay += delay
                    delay_count += 1
        
        avg_delay = total_delay / max(delay_count, 1) if delay_count > 0 else 0
        
        return {
            'loads': total_loads,
            'on_time_loads': on_time_loads,
            'on_time_percentage': round((on_time_loads / total_loads * 100), 1) if total_loads > 0 else 0,
            'avg_delay': round(avg_delay, 1)
        }
    
    # Calculate metrics for each period
    today_metrics = calculate_metrics(today_loads)
    yesterday_metrics = calculate_metrics(yesterday_loads)
    weekly_metrics = calculate_metrics(weekly_loads)
    monthly_metrics = calculate_metrics(monthly_loads)
    
    # Get milestone data
    milestones = Milestone.query.filter_by(driver_id=driver.id).order_by(Milestone.achieved_at.desc()).limit(5).all()
    
    milestone_data = [{
        'id': milestone.id,
        'type': milestone.type,
        'value': milestone.value,
        'achieved_at': milestone.achieved_at.strftime('%Y-%m-%d')
    } for milestone in milestones]
    
    # Create weekly trend data for chart (weekly intervals from May 2025)
    import datetime as dt
    weekly_data = []
    start_date = datetime(2025, 5, 1).date()
    
    # Generate 4 weeks of data (May 2025)
    for week in range(4):
        week_start = start_date + timedelta(weeks=week)
        week_end = week_start + timedelta(days=6)
        
        # Get loads for this week
        week_loads = [l for l in all_loads 
                     if week_start <= l.scheduled_pickup_time.date() <= week_end]
        
        if week_loads:
            metrics = calculate_metrics(week_loads)
            weekly_data.append({
                'date': week_start.strftime('%Y-%m-%d'),
                'week': f"Week {week + 1}",
                'loads': metrics['loads'],
                'on_time_percentage': metrics['on_time_percentage'],
                'avg_delay': metrics['avg_delay']
            })
    
    # Compile all data
    driver_data = {
        'id': driver.id,
        'name': driver.name,
        'phone': driver.phone,
        'email': driver.email,
        'motive_id': driver.motive_driver_id,
        'status': driver.status,
        'created_at': driver.created_at.strftime('%Y-%m-%d'),
        
        'metrics': {
            'today': today_metrics,
            'yesterday': yesterday_metrics,
            'weekly': weekly_metrics,
            'monthly': monthly_metrics
        },
        
        'loads': {
            'completed': completed_loads_data,
            'upcoming': upcoming_loads_data
        },
        
        'milestones': milestone_data,
        'weekly_performance': weekly_data
    }
    
    return jsonify(driver_data)

@drivers_bp.route("/api/drivers/locations")
def driver_locations():
    """API endpoint for real-time driver locations with ETA calculations"""
    drivers = get_active_driver_locations()
    destination = "123 Delivery St, Dallas TX"  # Default destination - should be configurable
    for driver in drivers:
        driver["eta"] = get_eta(driver["latitude"], driver["longitude"], destination)
    return jsonify(drivers)

@drivers_bp.route('/drivers/create', methods=['GET', 'POST'])
def create_driver():
    """Create a new driver"""
    if request.method == 'POST':
        try:
            data = request.form
            
            # Check if required fields are present
            if not data.get('name'):
                flash('Driver name is required', 'danger')
                return redirect(url_for('drivers.create_driver'))
            
            # Create new driver
            new_driver = Driver(
                name=data['name'],
                phone=data.get('phone', ''),
                email=data.get('email', ''),
                company=data.get('company', 'Hitched Logistics LLC'),
                motive_driver_id=data.get('motive_driver_id', ''),
                status='active'
            )
            
            db.session.add(new_driver)
            db.session.commit()
            
            flash('Driver created successfully', 'success')
            return redirect(url_for('drivers.driver_detail', driver_id=new_driver.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating driver: {str(e)}', 'danger')
            return redirect(url_for('drivers.create_driver'))
    
    # GET request - render form
    return render_template('driver_detail.html', driver=None)  # None indicates this is a create form

@drivers_bp.route('/drivers/<int:driver_id>/update', methods=['POST'])
def update_driver(driver_id):
    """Update an existing driver"""
    driver = Driver.query.get_or_404(driver_id)
    
    try:
        data = request.form
        
        # Update fields
        if data.get('name'):
            driver.name = data['name']
        
        if 'phone' in data:
            driver.phone = data['phone']
        
        if 'email' in data:
            driver.email = data['email']
        
        if 'company' in data:
            driver.company = data['company']
        
        if 'motive_driver_id' in data:
            driver.motive_driver_id = data['motive_driver_id']
        
        if 'status' in data:
            driver.status = data['status']
        
        db.session.commit()
        
        flash('Driver updated successfully', 'success')
        return redirect(url_for('drivers.driver_detail', driver_id=driver.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating driver: {str(e)}', 'danger')
        return redirect(url_for('drivers.driver_detail', driver_id=driver.id))

@drivers_bp.route('/drivers/<int:driver_id>/performance/update', methods=['POST'])
def update_performance(driver_id):
    """Manually update a driver's performance metrics"""
    driver = Driver.query.get_or_404(driver_id)
    
    try:
        data = request.json
        date_str = data.get('date')
        
        if not date_str:
            return jsonify({'error': 'Date is required'}), 400
        
        performance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Find or create performance record for the given date
        performance = DriverPerformance.query.filter_by(
            driver_id=driver.id, 
            date=performance_date
        ).first()
        
        if not performance:
            performance = DriverPerformance(
                driver_id=driver.id,
                date=performance_date
            )
            db.session.add(performance)
        
        # Update fields
        if 'loads_completed' in data:
            performance.loads_completed = data['loads_completed']
        
        if 'on_time_pickups' in data:
            performance.on_time_pickups = data['on_time_pickups']
        
        if 'on_time_deliveries' in data:
            performance.on_time_deliveries = data['on_time_deliveries']
        
        if 'average_delay_minutes' in data:
            performance.average_delay_minutes = data['average_delay_minutes']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'performance': {
                'date': performance.date.strftime('%Y-%m-%d'),
                'loads_completed': performance.loads_completed,
                'on_time_pickups': performance.on_time_pickups,
                'on_time_deliveries': performance.on_time_deliveries,
                'average_delay_minutes': performance.average_delay_minutes,
                'on_time_pickup_percentage': performance.on_time_pickup_percentage,
                'on_time_delivery_percentage': performance.on_time_delivery_percentage
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@drivers_bp.route('/drivers/scorecards')
def scorecards():
    """Show driver scorecards and rankings"""
    return render_template('scorecards.html')

@drivers_bp.route('/drivers/scorecards/data')
def get_scorecards_data():
    """API endpoint to get driver scorecard data"""
    period = request.args.get('period', 30, type=int)
    start_date_param = request.args.get('start_date')
    end_date_param = request.args.get('end_date')
    
    try:
        # Handle custom date range if provided
        if start_date_param and end_date_param:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_param, '%Y-%m-%d').date()
        else:
            # Calculate date range - for demo purposes, use May 2025 data
            end_date = datetime(2025, 5, 31).date()
            start_date = datetime(2025, 5, 1).date()
        
        # Get all drivers with their performance data
        drivers = db.session.query(Driver).all()
        scorecard_data = []
        
        for driver in drivers:
            # Get loads for this driver in the period
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            loads = db.session.query(Load).filter(
                Load.driver_id == driver.id,
                Load.scheduled_pickup_time >= start_datetime,
                Load.scheduled_pickup_time <= end_datetime
            ).all()
            
            if not loads:
                continue  # Skip drivers with no loads in this period
            
            # Calculate performance metrics
            total_loads = len(loads)
            on_time_pickups = sum(1 for load in loads if load.pickup_on_time == True)
            on_time_deliveries = sum(1 for load in loads if load.delivery_on_time == True)
            
            # Calculate average delay
            total_delay_minutes = 0
            delayed_loads = 0
            
            for load in loads:
                if load.actual_pickup_arrival and load.scheduled_pickup_time:
                    pickup_delay = (load.actual_pickup_arrival - load.scheduled_pickup_time).total_seconds() / 60
                    if pickup_delay > 0:  # Any delay is counted
                        total_delay_minutes += pickup_delay
                        delayed_loads += 1
                
                if load.actual_delivery_arrival and load.scheduled_delivery_time:
                    delivery_delay = (load.actual_delivery_arrival - load.scheduled_delivery_time).total_seconds() / 60
                    if delivery_delay > 0:  # Any delay is counted
                        total_delay_minutes += delivery_delay
                        delayed_loads += 1
            
            avg_delay = total_delay_minutes / max(delayed_loads, 1) if delayed_loads > 0 else 0
            
            # Calculate percentages
            on_time_pickup_pct = round((on_time_pickups / total_loads * 100), 1) if total_loads > 0 else 0
            on_time_delivery_pct = round((on_time_deliveries / total_loads * 100), 1) if total_loads > 0 else 0
            
            scorecard_data.append({
                'id': driver.id,
                'name': driver.name,
                'loads_completed': total_loads,
                'on_time_pickup_percentage': on_time_pickup_pct,
                'on_time_delivery_percentage': on_time_delivery_pct,
                'average_delay_minutes': round(avg_delay, 1),
                'overall_score': round((on_time_pickup_pct + on_time_delivery_pct) / 2, 1)
            })
        
        # Sort by overall score (descending) then by loads completed
        scorecard_data.sort(key=lambda x: (x['overall_score'], x['loads_completed']), reverse=True)
        
        return jsonify(scorecard_data)
        
    except Exception as e:
        logger.error(f"Error getting scorecard data: {e}")
        return jsonify({'error': 'Failed to load scorecard data'}), 500


