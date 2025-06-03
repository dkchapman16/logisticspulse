from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func, case
from models import Load, Driver, DriverPerformance, Notification
from app import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/dashboard/summary')
def dashboard_summary():
    """API endpoint for dashboard summary data"""
    from flask import request
    
    # Get parameters from request
    period = request.args.get('period', '30')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    driver_id = request.args.get('driver_id')
    
    # Calculate date range
    if start_date and end_date:
        try:
            date_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            date_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            date_start = datetime.utcnow().date() - timedelta(days=30)
            date_end = datetime.utcnow().date()
    else:
        try:
            days = int(period)
        except ValueError:
            days = 30
        date_end = datetime.utcnow().date()
        date_start = date_end - timedelta(days=days)
    
    # Build base query
    base_query = Load.query
    if driver_id:
        base_query = base_query.filter(Load.driver_id == driver_id)
    
    # Get active loads count
    active_loads = base_query.filter(Load.status.in_(['scheduled', 'in_transit'])).count()
    
    # Get on-time statistics for the date range
    on_time_pickups = base_query.filter(
        func.date(Load.actual_pickup_arrival) >= date_start,
        func.date(Load.actual_pickup_arrival) <= date_end,
        Load.actual_pickup_arrival <= Load.scheduled_pickup_time
    ).count()
    
    on_time_deliveries = base_query.filter(
        func.date(Load.actual_delivery_arrival) >= date_start,
        func.date(Load.actual_delivery_arrival) <= date_end,
        Load.actual_delivery_arrival <= Load.scheduled_delivery_time
    ).count()
    
    total_pickups = base_query.filter(
        func.date(Load.actual_pickup_arrival) >= date_start,
        func.date(Load.actual_pickup_arrival) <= date_end
    ).count()
    
    total_deliveries = base_query.filter(
        func.date(Load.actual_delivery_arrival) >= date_start,
        func.date(Load.actual_delivery_arrival) <= date_end
    ).count()
    
    # Calculate overall on-time (both pickup AND delivery on time)
    overall_on_time = base_query.filter(
        func.date(Load.actual_pickup_arrival) >= date_start,
        func.date(Load.actual_pickup_arrival) <= date_end,
        func.date(Load.actual_delivery_arrival) >= date_start,
        func.date(Load.actual_delivery_arrival) <= date_end,
        Load.actual_pickup_arrival <= Load.scheduled_pickup_time,
        Load.actual_delivery_arrival <= Load.scheduled_delivery_time
    ).count()
    
    # Get total completed loads (both pickup and delivery completed)
    total_completed = base_query.filter(
        func.date(Load.actual_pickup_arrival) >= date_start,
        func.date(Load.actual_pickup_arrival) <= date_end,
        func.date(Load.actual_delivery_arrival) >= date_start,
        func.date(Load.actual_delivery_arrival) <= date_end
    ).count()
    
    # Calculate percentages
    pickup_percentage = (on_time_pickups / total_pickups * 100) if total_pickups > 0 else 0
    delivery_percentage = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
    overall_percentage = (overall_on_time / total_completed * 100) if total_completed > 0 else 0
    
    # Get drivers with the best on-time performance using Load data directly
    if driver_id:
        # For individual driver view, get the specific driver's info
        selected_driver = Driver.query.get(driver_id)
        top_drivers = []
        if selected_driver:
            driver_loads = base_query.filter(
                func.date(Load.actual_delivery_arrival) >= date_start,
                func.date(Load.actual_delivery_arrival) <= date_end
            ).count()
            driver_on_time = base_query.filter(
                func.date(Load.actual_delivery_arrival) >= date_start,
                func.date(Load.actual_delivery_arrival) <= date_end,
                Load.actual_delivery_arrival <= Load.scheduled_delivery_time
            ).count()
            on_time_pct = (driver_on_time / driver_loads * 100) if driver_loads > 0 else 0
            top_drivers = [{'id': selected_driver.id, 'name': selected_driver.name, 'on_time_percentage': on_time_pct}]
    else:
        # For company view, get top performing drivers
        subquery = db.session.query(
            Load.driver_id,
            func.count(Load.id).label('total_loads'),
            func.sum(
                case(
                    (Load.actual_delivery_arrival <= Load.scheduled_delivery_time, 1),
                    else_=0
                )
            ).label('on_time_loads')
        ).filter(
            func.date(Load.actual_delivery_arrival) >= date_start,
            func.date(Load.actual_delivery_arrival) <= date_end,
            Load.driver_id.isnot(None)
        ).group_by(Load.driver_id).subquery()
        
        top_drivers_query = db.session.query(
            Driver.id,
            Driver.name,
            (subquery.c.on_time_loads * 100.0 / subquery.c.total_loads).label('on_time_percentage')
        ).join(subquery, Driver.id == subquery.c.driver_id).filter(
            subquery.c.total_loads >= 3  # Only drivers with at least 3 loads
        ).order_by((subquery.c.on_time_loads * 100.0 / subquery.c.total_loads).desc()).limit(5).all()
        
        top_drivers = [{'id': d.id, 'name': d.name, 'on_time_percentage': round(d.on_time_percentage, 1)} for d in top_drivers_query]
    
    # Get recent notifications
    recent_notifications = Notification.query.filter(
        Notification.read == False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Calculate late shipments and total deliveries
    late_deliveries = total_deliveries - on_time_deliveries
    
    # Get total driver count for company view
    total_drivers = Driver.query.filter_by(status='active').count()
    
    # Format the data for the response
    summary_data = {
        'active_loads': active_loads,
        'total_deliveries': total_deliveries,
        'late_deliveries': late_deliveries,
        'total_drivers': total_drivers,
        'on_time': {
            'pickup_percentage': round(pickup_percentage, 1),
            'delivery_percentage': round(delivery_percentage, 1),
            'overall_percentage': round(overall_percentage, 1)
        },
        'top_drivers': top_drivers,
        'notifications': [
            {
                'id': notification.id,
                'message': notification.message,
                'type': notification.type,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M')
            } for notification in recent_notifications
        ]
    }
    
    return jsonify(summary_data)

@dashboard_bp.route('/api/dashboard/at_risk_loads')
def at_risk_loads():
    """API endpoint for loads at risk of being late"""
    from datetime import datetime, timedelta
    from flask import request
    
    # Get current time
    current_time = datetime.utcnow()
    
    # Check if filtering by specific driver
    driver_id = request.args.get('driver_id', type=int)
    
    # Build base query
    query = Load.query.filter(
        Load.status.in_(['scheduled', 'in_transit']),
        Load.actual_delivery_arrival == None,
        Load.scheduled_delivery_time <= current_time + timedelta(hours=24)  # Due within 24 hours
    ).join(Driver, Load.driver_id == Driver.id, isouter=True)
    
    # Apply driver filter if specified
    if driver_id:
        query = query.filter(Load.driver_id == driver_id)
    
    at_risk_loads = query.all()
    
    # Filter for loads that are actually at risk (overdue or close to being overdue)
    filtered_loads = []
    for load in at_risk_loads:
        time_until_pickup = (load.scheduled_pickup_time - current_time).total_seconds() / 3600  # hours
        time_until_delivery = (load.scheduled_delivery_time - current_time).total_seconds() / 3600  # hours
        
        risk_info = None
        
        # Check pickup risk first
        if load.status == 'scheduled' and time_until_pickup < 0:
            # Pickup is overdue
            risk_info = {'type': 'pickup', 'delay_hours': abs(time_until_pickup)}
        elif load.status == 'scheduled' and time_until_pickup < 1:
            # Pickup is at risk (due within 1 hour)
            risk_info = {'type': 'pickup', 'delay_hours': time_until_pickup}
        # Check delivery risk
        elif time_until_delivery < 0:
            # Delivery is overdue
            risk_info = {'type': 'delivery', 'delay_hours': abs(time_until_delivery)}
        elif time_until_delivery < 2 and load.status == 'scheduled':
            # Delivery at risk and not even picked up
            risk_info = {'type': 'delivery', 'delay_hours': time_until_delivery}
        elif time_until_delivery < 4 and load.status == 'in_transit':
            # Delivery at risk while in transit
            risk_info = {'type': 'delivery', 'delay_hours': time_until_delivery}
        
        if risk_info:
            load.risk_info = risk_info
            filtered_loads.append(load)
    
    # Format the data for the response
    loads_data = []
    for load in filtered_loads[:10]:  # Limit to 10 most urgent
        risk_info = load.risk_info
        delay_minutes = int(risk_info['delay_hours'] * 60)
        abs_minutes = abs(delay_minutes)
        
        # Format time display
        if abs_minutes >= 60:
            hours = abs_minutes // 60
            minutes = abs_minutes % 60
            if minutes > 0:
                time_str = f"{hours}h {minutes}m"
            else:
                time_str = f"{hours}h"
        else:
            time_str = f"{abs_minutes}m"
        
        # Create specific risk labels
        milestone_type = risk_info['type'].title()  # "Pickup" or "Delivery"
        
        if delay_minutes < 0:
            risk_label = f"{milestone_type} Delayed {time_str}"
            risk_class = "danger"
        else:
            risk_label = f"{milestone_type} At Risk {time_str}"
            risk_class = "warning"
        
        pickup_facility = load.pickup_facility
        delivery_facility = load.delivery_facility
        
        loads_data.append({
            'id': load.id,
            'reference_number': load.reference_number,
            'driver_name': load.driver.name if load.driver else 'Unassigned',
            'driver_id': load.driver.id if load.driver else None,
            'origin': f"{pickup_facility.city}, {pickup_facility.state}" if pickup_facility else "Unknown",
            'destination': f"{delivery_facility.city}, {delivery_facility.state}" if delivery_facility else "Unknown",
            'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
            'risk_label': risk_label,
            'risk_class': risk_class,
            'delay_minutes': abs_minutes
        })
    
    return jsonify(loads_data)

@dashboard_bp.route('/api/dashboard/performance_trends')
def performance_trends():
    """API endpoint for performance trend data over the past 30 days"""
    from flask import request
    
    # Get today's date and date 30 days ago
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Check if filtering by specific driver
    driver_id = request.args.get('driver_id', type=int)
    
    # Build base query using Load data directly
    query = Load.query.filter(
        Load.actual_delivery_arrival.isnot(None),
        func.date(Load.actual_delivery_arrival) >= thirty_days_ago,
        func.date(Load.actual_delivery_arrival) <= today
    )
    
    # Apply driver filter if specified
    if driver_id:
        query = query.filter(Load.driver_id == driver_id)
    
    # Get daily aggregated data from Load records
    daily_data = query.with_entities(
        func.date(Load.actual_delivery_arrival).label('date'),
        func.count(Load.id).label('total_loads'),
        func.sum(
            case(
                (Load.actual_pickup_arrival <= Load.scheduled_pickup_time, 1),
                else_=0
            )
        ).label('on_time_pickups'),
        func.sum(
            case(
                (Load.actual_delivery_arrival <= Load.scheduled_delivery_time, 1),
                else_=0
            )
        ).label('on_time_deliveries')
    ).group_by(func.date(Load.actual_delivery_arrival)).order_by(func.date(Load.actual_delivery_arrival)).all()
    
    # Format the data for the response
    trend_data = []
    for entry in daily_data:
        pickup_pct = round((entry.on_time_pickups / entry.total_loads * 100), 1) if entry.total_loads > 0 else 0
        delivery_pct = round((entry.on_time_deliveries / entry.total_loads * 100), 1) if entry.total_loads > 0 else 0
        
        trend_data.append({
            'date': entry.date.strftime('%Y-%m-%d'),
            'loads': entry.total_loads,
            'on_time_pickup_percentage': pickup_pct,
            'on_time_delivery_percentage': delivery_pct,
            'avg_delay_minutes': 0  # We can calculate this later if needed
        })
    
    return jsonify(trend_data)
