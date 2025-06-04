from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime, timedelta
from models import db, Driver, Load, Client, Facility
from services.notification_service import send_notification
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

availability_bp = Blueprint('availability', __name__)
logger = logging.getLogger(__name__)

@availability_bp.route('/availability')
def index():
    """Show truck availability broadcast interface"""
    return render_template('availability.html')

@availability_bp.route('/availability/fleet-status')
def get_fleet_status():
    """API endpoint to get current fleet availability status for email blast"""
    try:
        # Get all active drivers and their current status
        drivers = db.session.query(Driver).filter_by(status='active').all()
        
        available_trucks = []
        upcoming_availability = []
        
        for driver in drivers:
            # Get the most recent load for this driver
            latest_load = db.session.query(Load).filter(
                Load.driver_id == driver.id
            ).order_by(Load.scheduled_delivery_time.desc()).first()
            
            # Get delivery facility if it exists
            delivery_facility = None
            if latest_load and latest_load.delivery_facility_id:
                delivery_facility = db.session.query(Facility).get(latest_load.delivery_facility_id)
            
            if not latest_load:
                # Driver has no loads - available immediately
                available_trucks.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': "Available for dispatch",
                    'available_date': datetime.now().strftime('%m/%d/%Y'),
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available Now'
                })
            elif latest_load.status == 'delivered':
                # Recently delivered - available now
                location = "Location TBD"
                if delivery_facility:
                    location = f"{delivery_facility.city}, {delivery_facility.state}"
                
                available_trucks.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': location,
                    'available_date': datetime.now().strftime('%m/%d/%Y'),
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available Now'
                })
            elif latest_load.status == 'in_transit' and latest_load.scheduled_delivery_time:
                # In transit - will be available after delivery
                location = "En route"
                if delivery_facility:
                    location = f"Delivering to {delivery_facility.city}, {delivery_facility.state}"
                
                upcoming_availability.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': location,
                    'available_date': latest_load.scheduled_delivery_time.strftime('%m/%d/%Y'),
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available Soon'
                })
        
        return jsonify({
            'available_now': available_trucks,
            'upcoming_availability': upcoming_availability,
            'total_available': len(available_trucks),
            'total_upcoming': len(upcoming_availability),
            'report_date': datetime.now().strftime('%B %d, %Y')
        })
        
    except Exception as e:
        logger.error(f"Error getting fleet status: {e}")
        return jsonify({'error': 'Failed to load fleet status'}), 500

@availability_bp.route('/availability/generate-email-template', methods=['POST'])
def generate_email_template():
    """Generate HTML email template for manual sending"""
    try:
        data = request.get_json()
        subject = data.get('subject', 'Weekly Fleet Availability Update')
        from_email = data.get('from_email', 'dispatch@hitchedlogistics.com')
        
        # Get contact information from the request, use "x" for empty fields
        contact_info = {
            'email': data.get('contact_email', '').strip() or 'x',
            'phone': data.get('contact_phone', '').strip() or 'x',
            'name': data.get('contact_name', '').strip() or 'x',
            'hours': data.get('availability_hours', '').strip() or 'x'
        }
        
        # Get current fleet status
        drivers = db.session.query(Driver).filter_by(status='active').all()
        
        available_trucks = []
        upcoming_availability = []
        
        for driver in drivers:
            latest_load = db.session.query(Load).filter(
                Load.driver_id == driver.id
            ).order_by(Load.scheduled_delivery_time.desc()).first()
            
            delivery_facility = None
            if latest_load and latest_load.delivery_facility_id:
                delivery_facility = db.session.query(Facility).get(latest_load.delivery_facility_id)
            
            if not latest_load:
                available_trucks.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': "Available for dispatch",
                    'available_date': datetime.now().strftime('%m/%d/%Y'),
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available Now'
                })
            elif latest_load.status == 'delivered':
                location = "Location TBD"
                if delivery_facility:
                    location = f"{delivery_facility.city}, {delivery_facility.state}"
                
                available_trucks.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': location,
                    'available_date': datetime.now().strftime('%m/%d/%Y'),
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available Now'
                })
            elif latest_load.status == 'in_transit' and latest_load.scheduled_delivery_time:
                location = "En route"
                if delivery_facility:
                    location = f"Delivering to {delivery_facility.city}, {delivery_facility.state}"
                
                # Include both date and time for upcoming availability
                delivery_datetime = latest_load.scheduled_delivery_time.strftime('%m/%d/%Y at %I:%M %p')
                
                upcoming_availability.append({
                    'driver_name': driver.name,
                    'truck_info': f"Driver: {driver.name}",
                    'current_location': location,
                    'available_date': delivery_datetime,
                    'contact_info': driver.phone or "Contact dispatch",
                    'status': 'Available after delivery'
                })
        
        fleet_data = {
            'available_now': available_trucks,
            'upcoming_availability': upcoming_availability,
            'total_available': len(available_trucks),
            'total_upcoming': len(upcoming_availability),
            'report_date': datetime.now().strftime('%B %d, %Y')
        }
        
        # Generate HTML email content with contact info
        html_content = generate_availability_email_html(fleet_data, contact_info)
        
        # Generate plain text version for copying with contact info
        plain_text = generate_plain_text_email(fleet_data, contact_info)
        
        return jsonify({
            'success': True,
            'subject': subject,
            'from_email': from_email,
            'html_content': html_content,
            'plain_text': plain_text,
            'available_count': fleet_data['total_available'],
            'upcoming_count': fleet_data['total_upcoming'],
            'message': 'Email template generated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sending email blast: {e}")
        return jsonify({'error': 'Failed to generate email blast'}), 500

def generate_availability_email_html(fleet_data, contact_info=None):
    """Generate professional HTML email content for availability report"""
    if contact_info is None:
        contact_info = {
            'email': 'x',
            'phone': 'x',
            'name': 'x',
            'hours': 'x'
        }
    
    current_date = datetime.now().strftime('%B %d, %Y')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Fleet Availability Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background-color: #00c48c; color: white; padding: 20px; margin: -30px -30px 30px -30px; border-radius: 8px 8px 0 0; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .header p {{ margin: 5px 0 0 0; opacity: 0.9; }}
            .section {{ margin-bottom: 30px; }}
            .section h2 {{ color: #333; border-bottom: 2px solid #00c48c; padding-bottom: 10px; }}
            .truck-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            .truck-table th, .truck-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            .truck-table th {{ background-color: #f8f9fa; font-weight: bold; color: #333; }}
            .status-available {{ color: #28a745; font-weight: bold; }}
            .status-soon {{ color: #ffc107; font-weight: bold; }}
            .contact-info {{ background-color: #e9ecef; padding: 20px; border-radius: 5px; margin-top: 30px; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Hitched Logistics LLC</h1>
                <p>Weekly Fleet Availability Report - {current_date}</p>
            </div>
            
            <div class="section">
                <h2>🚛 Available Now ({fleet_data.get('total_available', 0)} Trucks)</h2>
                <table class="truck-table">
                    <thead>
                        <tr>
                            <th>Driver</th>
                            <th>Current Location</th>
                            <th>Available Date</th>
                            <th>Contact</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    # Add available trucks
    for truck in fleet_data.get('available_now', []):
        html += f"""
                        <tr>
                            <td>{truck['driver_name']}</td>
                            <td>{truck['current_location']}</td>
                            <td>{truck['available_date']}</td>
                            <td>{truck['contact_info']}</td>
                        </tr>
        """
    
    html += """
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>📅 Upcoming Availability ({}) Trucks)</h2>
                <table class="truck-table">
                    <thead>
                        <tr>
                            <th>Driver</th>
                            <th>Current Status</th>
                            <th>Available Date & Time</th>
                            <th>Contact</th>
                        </tr>
                    </thead>
                    <tbody>
    """.format(fleet_data.get('total_upcoming', 0))
    
    # Add upcoming availability
    for truck in fleet_data.get('upcoming_availability', []):
        html += f"""
                        <tr>
                            <td>{truck['driver_name']}</td>
                            <td>{truck['current_location']}</td>
                            <td>{truck['available_date']}</td>
                            <td>{truck['contact_info']}</td>
                        </tr>
        """
    
    html += f"""
                    </tbody>
                </table>
            </div>
            
            <div class="contact-info">
                <h3>📞 Contact Information</h3>
                <p><strong>Contact our {contact_info['name']}:</strong></p>
                <p>📧 Email: {contact_info['email']}</p>
                <p>📱 Phone: {contact_info['phone']}</p>
                <p>🕒 {contact_info['hours']}</p>
            </div>
            
            <div class="footer">
                <p>Hitched Logistics LLC</p>
                <p>This report was generated on {current_date}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generate_plain_text_email(fleet_data, contact_info=None):
    """Generate plain text email for copy/paste"""
    if contact_info is None:
        contact_info = {
            'email': 'x',
            'phone': 'x',
            'name': 'x',
            'hours': 'x'
        }
    
    current_date = datetime.now().strftime('%B %d, %Y')
    
    text = f"""HITCHED LOGISTICS LLC
Weekly Fleet Availability Report - {current_date}

🚛 AVAILABLE NOW ({fleet_data.get('total_available', 0)} TRUCKS)
{"=" * 50}
"""
    
    # Add available trucks
    for truck in fleet_data.get('available_now', []):
        text += f"""
Driver: {truck['driver_name']}
Location: {truck['current_location']}
Available: {truck['available_date']}
Contact: {truck['contact_info']}
---
"""
    
    text += f"""

📅 UPCOMING AVAILABILITY ({fleet_data.get('total_upcoming', 0)} TRUCKS)
{"=" * 50}
"""
    
    # Add upcoming availability
    for truck in fleet_data.get('upcoming_availability', []):
        text += f"""
Driver: {truck['driver_name']}
Current Status: {truck['current_location']}
Available: {truck['available_date']}
Contact: {truck['contact_info']}
---
"""
    
    text += f"""

📞 CONTACT INFORMATION
Contact our {contact_info['name']}:
📧 Email: {contact_info['email']}
📱 Phone: {contact_info['phone']}
🕒 {contact_info['hours']}

Hitched Logistics LLC
This report was generated on {current_date}
"""
    
    return text

@availability_bp.route('/availability/templates')
def get_message_templates():
    """Get predefined message templates for availability broadcasts"""
    templates = [
        {
            'name': 'Standard Availability',
            'message': 'TRUCK AVAILABLE: {driver_name} has completed delivery in {location} and is available for immediate pickup. Contact: {phone} - {company}'
        },
        {
            'name': 'Available Soon',
            'message': 'TRUCK AVAILABLE SOON: {driver_name} will be available in {location} within the hour. Reserve now! Contact: {phone} - {company}'
        },
        {
            'name': 'Capacity Available',
            'message': 'CAPACITY ALERT: {driver_name} has truck capacity available from {location}. Book your shipment today! {phone} - {company}'
        },
        {
            'name': 'Regional Coverage',
            'message': 'REGIONAL COVERAGE: {driver_name} available for pickups in the {location} area. Reliable service guaranteed. {phone} - {company}'
        }
    ]
    
    return jsonify({'templates': templates})

@availability_bp.route('/availability/history')
def broadcast_history():
    """Get history of availability broadcasts"""
    try:
        # For now, return recent notifications related to availability
        # In a full implementation, you'd have a dedicated broadcast history table
        
        return jsonify({
            'broadcasts': [],
            'total_count': 0
        })
        
    except Exception as e:
        logger.error(f"Error getting broadcast history: {e}")
        return jsonify({'error': 'Failed to load broadcast history'}), 500