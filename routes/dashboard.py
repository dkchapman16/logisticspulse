from flask import Blueprint, render_template, jsonify
from datetime import datetime, timedelta
from sqlalchemy import func
from models import Load, Driver, DriverPerformance, Notification

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
    
    # Calculate percentages
    pickup_percentage = (on_time_pickups / total_pickups * 100) if total_pickups > 0 else 0
    delivery_percentage = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
    
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
    
    # Format the data for the response
    summary_data = {
        'active_loads': active_loads,
        'on_time': {
            'pickup_percentage': round(pickup_percentage, 1),
            'delivery_percentage': round(delivery_percentage, 1)
        },
        'top_drivers': [
            {
                'id': driver.id,
                'name': driver.name,
                'on_time_percentage': round(driver.on_time_percentage, 1)
            } for driver in top_drivers
        ],
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
    # Get loads that are in transit and have an ETA after the scheduled delivery time
    at_risk_loads = Load.query.filter(
        Load.status == 'in_transit',
        Load.current_eta > Load.scheduled_delivery_time,
        Load.actual_delivery_arrival == None
    ).join(Driver).all()
    
    # Format the data for the response
    loads_data = [
        {
            'id': load.id,
            'reference_number': load.reference_number,
            'driver_name': load.driver.name if load.driver else 'Unassigned',
            'scheduled_delivery': load.scheduled_delivery_time.strftime('%Y-%m-%d %H:%M'),
            'current_eta': load.current_eta.strftime('%Y-%m-%d %H:%M') if load.current_eta else None,
            'delay_minutes': round((load.current_eta - load.scheduled_delivery_time).total_seconds() / 60) if load.current_eta else None
        } for load in at_risk_loads
    ]
    
    return jsonify(loads_data)

@dashboard_bp.route('/api/dashboard/performance_trends')
def performance_trends():
    """API endpoint for performance trend data over the past 30 days"""
    # Get today's date and date 30 days ago
    today = datetime.utcnow().date()
    thirty_days_ago = today - timedelta(days=30)
    
    # Get daily performance data for the past 30 days
    daily_performance = DriverPerformance.query.filter(
        DriverPerformance.date >= thirty_days_ago,
        DriverPerformance.date <= today
    ).with_entities(
        DriverPerformance.date,
        func.sum(DriverPerformance.loads_completed).label('loads'),
        func.sum(DriverPerformance.on_time_pickups).label('on_time_pickups'),
        func.sum(DriverPerformance.on_time_deliveries).label('on_time_deliveries'),
        func.avg(DriverPerformance.average_delay_minutes).label('avg_delay')
    ).group_by(DriverPerformance.date).order_by(DriverPerformance.date).all()
    
    # Format the data for the response
    trend_data = [
        {
            'date': entry.date.strftime('%Y-%m-%d'),
            'loads': entry.loads,
            'on_time_pickup_percentage': round((entry.on_time_pickups / entry.loads * 100), 1) if entry.loads > 0 else 0,
            'on_time_delivery_percentage': round((entry.on_time_deliveries / entry.loads * 100), 1) if entry.loads > 0 else 0,
            'avg_delay_minutes': round(entry.avg_delay, 1)
        } for entry in daily_performance
    ]
    
    return jsonify(trend_data)
