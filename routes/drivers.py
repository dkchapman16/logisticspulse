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
    
    # Order by name
    query = query.order_by(Driver.name)
    
    # Paginate results
    drivers_page = query.paginate(page=page, per_page=per_page)
    
    # Format response data
    today = datetime.utcnow().date()
    month_ago = today - timedelta(days=30)
    
    drivers_data = []
    for driver in drivers_page.items:
        # Get performance data
        performances = DriverPerformance.query.filter(
            DriverPerformance.driver_id == driver.id,
            DriverPerformance.date >= month_ago
        ).all()
        
        total_loads = sum(p.loads_completed for p in performances)
        on_time_pickups = sum(p.on_time_pickups for p in performances)
        on_time_deliveries = sum(p.on_time_deliveries for p in performances)
        
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
        'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
        'actual_delivery': load.actual_delivery_arrival.strftime('%Y-%m-%d %H:%M') if load.actual_delivery_arrival else None,
        'on_time': load.delivery_on_time
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
    
    # Get performance metrics for different time periods
    daily_performance = DriverPerformance.query.filter(
        DriverPerformance.driver_id == driver.id,
        DriverPerformance.date >= month_ago
    ).order_by(DriverPerformance.date).all()
    
    # Calculate aggregated metrics
    today_perf = next((p for p in daily_performance if p.date == today), None)
    yesterday_perf = next((p for p in daily_performance if p.date == yesterday), None)
    
    weekly_perf = [p for p in daily_performance if p.date >= week_ago]
    monthly_perf = daily_performance  # All performances are from the last month
    
    # Calculate aggregated metrics
    today_metrics = {
        'loads': today_perf.loads_completed if today_perf else 0,
        'on_time_pickups': today_perf.on_time_pickups if today_perf else 0,
        'on_time_deliveries': today_perf.on_time_deliveries if today_perf else 0,
        'pickup_percentage': today_perf.on_time_pickup_percentage if today_perf else 0,
        'delivery_percentage': today_perf.on_time_delivery_percentage if today_perf else 0,
        'avg_delay': today_perf.average_delay_minutes if today_perf else 0
    }
    
    yesterday_metrics = {
        'loads': yesterday_perf.loads_completed if yesterday_perf else 0,
        'on_time_pickups': yesterday_perf.on_time_pickups if yesterday_perf else 0,
        'on_time_deliveries': yesterday_perf.on_time_deliveries if yesterday_perf else 0,
        'pickup_percentage': yesterday_perf.on_time_pickup_percentage if yesterday_perf else 0,
        'delivery_percentage': yesterday_perf.on_time_delivery_percentage if yesterday_perf else 0,
        'avg_delay': yesterday_perf.average_delay_minutes if yesterday_perf else 0
    }
    
    weekly_loads = sum(p.loads_completed for p in weekly_perf)
    weekly_pickups = sum(p.on_time_pickups for p in weekly_perf)
    weekly_deliveries = sum(p.on_time_deliveries for p in weekly_perf)
    
    weekly_metrics = {
        'loads': weekly_loads,
        'on_time_pickups': weekly_pickups,
        'on_time_deliveries': weekly_deliveries,
        'pickup_percentage': round((weekly_pickups / weekly_loads * 100), 1) if weekly_loads > 0 else 0,
        'delivery_percentage': round((weekly_deliveries / weekly_loads * 100), 1) if weekly_loads > 0 else 0,
        'avg_delay': round(sum(p.average_delay_minutes for p in weekly_perf) / len(weekly_perf), 1) if weekly_perf else 0
    }
    
    monthly_loads = sum(p.loads_completed for p in monthly_perf)
    monthly_pickups = sum(p.on_time_pickups for p in monthly_perf)
    monthly_deliveries = sum(p.on_time_deliveries for p in monthly_perf)
    
    monthly_metrics = {
        'loads': monthly_loads,
        'on_time_pickups': monthly_pickups,
        'on_time_deliveries': monthly_deliveries,
        'pickup_percentage': round((monthly_pickups / monthly_loads * 100), 1) if monthly_loads > 0 else 0,
        'delivery_percentage': round((monthly_deliveries / monthly_loads * 100), 1) if monthly_loads > 0 else 0,
        'avg_delay': round(sum(p.average_delay_minutes for p in monthly_perf) / len(monthly_perf), 1) if monthly_perf else 0
    }
    
    # Get milestone data
    milestones = Milestone.query.filter_by(driver_id=driver.id).order_by(Milestone.achieved_at.desc()).limit(5).all()
    
    milestone_data = [{
        'id': milestone.id,
        'type': milestone.type,
        'value': milestone.value,
        'achieved_at': milestone.achieved_at.strftime('%Y-%m-%d')
    } for milestone in milestones]
    
    # Format daily performance for chart
    daily_data = [{
        'date': perf.date.strftime('%Y-%m-%d'),
        'loads': perf.loads_completed,
        'pickup_percentage': perf.on_time_pickup_percentage,
        'delivery_percentage': perf.on_time_delivery_percentage,
        'avg_delay': perf.average_delay_minutes
    } for perf in daily_performance]
    
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
        'daily_performance': daily_data
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
            loads = db.session.query(Load).filter(
                Load.driver_id == driver.id,
                Load.scheduled_pickup_time >= start_date,
                Load.scheduled_pickup_time <= end_date
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
                    if pickup_delay > 30:  # More than 30 minutes late
                        total_delay_minutes += pickup_delay
                        delayed_loads += 1
                
                if load.actual_delivery_arrival and load.scheduled_delivery_time:
                    delivery_delay = (load.actual_delivery_arrival - load.scheduled_delivery_time).total_seconds() / 60
                    if delivery_delay > 30:  # More than 30 minutes late
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


