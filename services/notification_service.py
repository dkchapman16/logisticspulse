import logging
import os
from datetime import datetime
from app import db
from models import Notification, User, Load, Driver

logger = logging.getLogger(__name__)

def send_notification(user_id, message, notification_type='info', load_id=None, driver_id=None):
    """
    Create and send a notification to a user
    
    Args:
        user_id (int): User ID to send notification to
        message (str): Notification message
        notification_type (str): Type of notification (info, warning, danger, success)
        load_id (int, optional): Related load ID
        driver_id (int, optional): Related driver ID
    
    Returns:
        dict: Result of sending the notification
    """
    try:
        # Create notification record
        notification = Notification(
            user_id=user_id,
            load_id=load_id,
            driver_id=driver_id,
            type=notification_type,
            message=message,
            read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Get user details for sending notification
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found for ID {user_id}")
            return {
                'success': False,
                'error': 'User not found'
            }
        
        # In a real application, this would send SMS, email, or push notification
        # For now, we'll just log it
        logger.info(f"Notification sent to {user.username}: {message}")
        
        # Return success response
        return {
            'success': True,
            'notification': {
                'id': notification.id,
                'type': notification.type,
                'message': notification.message,
                'created_at': notification.created_at.isoformat()
            }
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending notification: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def send_late_risk_notification(load_id):
    """
    Send notification for a load at risk of being late
    
    Args:
        load_id (int): Load ID
    
    Returns:
        dict: Result of sending the notification
    """
    try:
        load = Load.query.get(load_id)
        
        if not load:
            logger.error(f"Load not found for ID {load_id}")
            return {
                'success': False,
                'error': 'Load not found'
            }
        
        # Calculate minutes late
        if not load.current_eta or not load.scheduled_delivery_time:
            return {
                'success': False,
                'error': 'Missing ETA or scheduled delivery time'
            }
        
        minutes_late = (load.current_eta - load.scheduled_delivery_time).total_seconds() / 60
        
        if minutes_late <= 0:
            # Not late, don't send notification
            return {
                'success': False,
                'error': 'Load is not at risk of being late'
            }
        
        # Format message
        driver_name = load.driver.name if load.driver else "Unassigned driver"
        message = f"LATE RISK: Load #{load.reference_number} with {driver_name} is "
        
        if minutes_late < 60:
            message += f"at risk of being {int(minutes_late)} minutes late for delivery."
        else:
            hours_late = minutes_late / 60
            message += f"at risk of being {hours_late:.1f} hours late for delivery."
        
        # Get dispatchers to notify (all users for now)
        dispatchers = User.query.all()
        
        results = []
        for dispatcher in dispatchers:
            result = send_notification(
                user_id=dispatcher.id,
                message=message,
                notification_type='warning',
                load_id=load.id,
                driver_id=load.driver_id
            )
            results.append(result)
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error sending late risk notification: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def send_arrival_notification(load_id, facility_type):
    """
    Send notification for load arrival
    
    Args:
        load_id (int): Load ID
        facility_type (str): 'pickup' or 'delivery'
    
    Returns:
        dict: Result of sending the notification
    """
    try:
        load = Load.query.get(load_id)
        
        if not load:
            logger.error(f"Load not found for ID {load_id}")
            return {
                'success': False,
                'error': 'Load not found'
            }
        
        # Check if arrival time exists
        arrival_time = None
        facility_name = None
        on_time = None
        
        if facility_type == 'pickup':
            arrival_time = load.actual_pickup_arrival
            scheduled_time = load.scheduled_pickup_time
            on_time = load.pickup_on_time
            facility_name = load.pickup_facility.name if load.pickup_facility else "pickup location"
        elif facility_type == 'delivery':
            arrival_time = load.actual_delivery_arrival
            scheduled_time = load.scheduled_delivery_time
            on_time = load.delivery_on_time
            facility_name = load.delivery_facility.name if load.delivery_facility else "delivery location"
        else:
            return {
                'success': False,
                'error': 'Invalid facility type'
            }
        
        if not arrival_time:
            return {
                'success': False,
                'error': f'No arrival time for {facility_type}'
            }
        
        # Format message
        driver_name = load.driver.name if load.driver else "Unassigned driver"
        
        if on_time:
            message = f"ON TIME: Load #{load.reference_number} with {driver_name} has arrived at {facility_name} on time."
            notification_type = 'success'
        else:
            # Calculate minutes late
            minutes_late = (arrival_time - scheduled_time).total_seconds() / 60
            
            if minutes_late < 60:
                message = f"LATE ARRIVAL: Load #{load.reference_number} with {driver_name} has arrived at {facility_name} {int(minutes_late)} minutes late."
            else:
                hours_late = minutes_late / 60
                message = f"LATE ARRIVAL: Load #{load.reference_number} with {driver_name} has arrived at {facility_name} {hours_late:.1f} hours late."
            
            notification_type = 'danger'
        
        # Get dispatchers to notify (all users for now)
        dispatchers = User.query.all()
        
        results = []
        for dispatcher in dispatchers:
            result = send_notification(
                user_id=dispatcher.id,
                message=message,
                notification_type=notification_type,
                load_id=load.id,
                driver_id=load.driver_id
            )
            results.append(result)
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error sending arrival notification: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def send_milestone_notification(driver_id, milestone_type, value):
    """
    Send notification for driver milestone achievement
    
    Args:
        driver_id (int): Driver ID
        milestone_type (str): Type of milestone (consecutive_on_time, monthly_perfect, etc.)
        value (int): Milestone value
    
    Returns:
        dict: Result of sending the notification
    """
    try:
        driver = Driver.query.get(driver_id)
        
        if not driver:
            logger.error(f"Driver not found for ID {driver_id}")
            return {
                'success': False,
                'error': 'Driver not found'
            }
        
        # Format message based on milestone type
        message = f"MILESTONE: {driver.name} has achieved "
        
        if milestone_type == 'consecutive_on_time':
            message += f"{value} consecutive on-time deliveries!"
        elif milestone_type == 'monthly_perfect':
            message += f"perfect on-time performance for {value} month(s)!"
        elif milestone_type == 'total_loads':
            message += f"{value} total loads delivered!"
        else:
            message += f"a new milestone: {milestone_type} with value {value}!"
        
        # Get dispatchers to notify (all users for now)
        dispatchers = User.query.all()
        
        results = []
        for dispatcher in dispatchers:
            result = send_notification(
                user_id=dispatcher.id,
                message=message,
                notification_type='success',
                driver_id=driver.id
            )
            results.append(result)
        
        return {
            'success': True,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error sending milestone notification: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
