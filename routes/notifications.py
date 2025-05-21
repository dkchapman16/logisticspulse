from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from models import Notification, User, Load, Driver
from services.notification_service import send_notification

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications')
@login_required
def index():
    """Show notifications interface"""
    return render_template('notifications.html')

@notifications_bp.route('/notifications/data')
@login_required
def get_notifications():
    """API endpoint to get notifications with pagination and filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread_only', 'false') == 'true'
    
    query = Notification.query
    
    # Filter by current user
    query = query.filter(Notification.user_id == current_user.id)
    
    # Apply unread filter if requested
    if unread_only:
        query = query.filter(Notification.read == False)
    
    # Order by most recent first
    query = query.order_by(Notification.created_at.desc())
    
    # Paginate results
    notifications_page = query.paginate(page=page, per_page=per_page)
    
    # Format response data
    notifications_data = []
    for notification in notifications_page.items:
        load_info = None
        if notification.load:
            load_info = {
                'id': notification.load.id,
                'reference_number': notification.load.reference_number
            }
            
        driver_info = None
        if notification.driver:
            driver_info = {
                'id': notification.driver.id,
                'name': notification.driver.name
            }
            
        notifications_data.append({
            'id': notification.id,
            'type': notification.type,
            'message': notification.message,
            'read': notification.read,
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M'),
            'load': load_info,
            'driver': driver_info
        })
    
    return jsonify({
        'notifications': notifications_data,
        'page': page,
        'per_page': per_page,
        'total': notifications_page.total,
        'pages': notifications_page.pages,
        'unread_count': Notification.query.filter_by(user_id=current_user.id, read=False).count()
    })

@notifications_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_read():
    """Mark notifications as read"""
    try:
        data = request.json
        notification_ids = data.get('notification_ids', [])
        
        if not notification_ids:
            return jsonify({'error': 'No notification IDs provided'}), 400
        
        # Make sure the user can only mark their own notifications as read
        notifications = Notification.query.filter(
            Notification.id.in_(notification_ids),
            Notification.user_id == current_user.id
        ).all()
        
        for notification in notifications:
            notification.read = True
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'marked_count': len(notifications),
            'unread_count': Notification.query.filter_by(user_id=current_user.id, read=False).count()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    try:
        # Update all unread notifications for the current user
        updated = Notification.query.filter_by(
            user_id=current_user.id,
            read=False
        ).update({'read': True})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'marked_count': updated,
            'unread_count': 0
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/notifications/create', methods=['POST'])
@login_required
def create_notification():
    """Create a new notification (for testing)"""
    try:
        data = request.json
        
        if not data.get('message'):
            return jsonify({'error': 'Message is required'}), 400
        
        # Get load and driver if IDs are provided
        load_id = data.get('load_id')
        driver_id = data.get('driver_id')
        
        load = Load.query.get(load_id) if load_id else None
        driver = Driver.query.get(driver_id) if driver_id else None
        
        # Create the notification
        notification = Notification(
            user_id=current_user.id,
            load_id=load.id if load else None,
            driver_id=driver.id if driver else None,
            type=data.get('type', 'info'),
            message=data['message'],
            read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        
        # Send the notification through the service
        if data.get('send', False):
            send_notification(
                user_id=current_user.id,
                message=data['message'],
                notification_type=data.get('type', 'info'),
                load_id=load.id if load else None,
                driver_id=driver.id if driver else None
            )
        
        return jsonify({
            'success': True,
            'notification': {
                'id': notification.id,
                'type': notification.type,
                'message': notification.message,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@notifications_bp.route('/notifications/count')
@login_required
def get_unread_count():
    """Get count of unread notifications"""
    count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
    return jsonify({
        'unread_count': count
    })
