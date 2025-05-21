from flask import Blueprint, render_template, jsonify
from flask_login import login_required
from datetime import datetime, timedelta
from sqlalchemy import func
from models import Load, Driver, DriverPerformance, Notification

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    return render_template('dashboard.html')

@dashboard_bp.route('/api/dashboard/summary')
@login_required
def dashboard_summary():
    """API endpoint for dashboard summary data"""
    # Get today's date and dates for weekly/monthly ranges
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Get active loads count
    active_loads = Load.query.filter(Load.status.in_(['scheduled', 'in_transit'])).count()
    
    # Get on-time statistics
    on_time_pickups_today = Load.query.filter(
        func.date(Load.actual_pickup_arrival) == today,
        Load.actual_pickup_arrival <= Load.scheduled_pickup_time
    ).count()
    
    on_time_deliveries_today = Load.query.filter(
        func.date(Load.actual_delivery_arrival) == today,
        Load.actual_delivery_arrival <= Load.scheduled_delivery_time
    ).count()
    
    total_pickups_today = Load.query.filter(
        func.date(Load.actual_pickup_arrival) == today
    ).count()
    
    total_deliveries_today = Load.query.filter(
        func.date(Load.actual_delivery_arrival) == today
    ).count()
    
    # Calculate percentages
    pickup_percentage = (on_time_pickups_today / total_pickups_today * 100) if total_pickups_today > 0 else 0
    delivery_percentage = (on_time_deliveries_today / total_deliveries_today * 100) if total_deliveries_today > 0 else 0
    
    # Get drivers with the best on-time performance
    top_drivers = DriverPerformance.query.filter(
        DriverPerformance.date >= month_ago
    ).join(Driver).with_entities(
        Driver.id,
        Driver.name,
        func.avg(DriverPerformance.on_time_deliveries / DriverPerformance.loads_completed * 100).label('on_time_percentage')
    ).group_by(Driver.id).order_by(func.avg(DriverPerformance.on_time_deliveries / DriverPerformance.loads_completed * 100).desc()).limit(5).all()
    
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
@login_required
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
@login_required
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
