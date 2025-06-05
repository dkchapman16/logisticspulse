"""
Temp Stick API integration for reefer trailer temperature monitoring
"""
import os
import requests
import gzip
import json
from datetime import datetime, timedelta
from services.logger import setup_logger

logger = setup_logger(__name__)

TEMP_STICK_API_KEY = os.environ.get('TEMP_STICK_API_KEY')
BASE_URL = 'https://tempstickapi.com/api/v1'


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit using the formula: (C * 1.8) + 32"""
    if celsius is None:
        return None
    return (celsius * 1.8) + 32


def make_api_request(endpoint, params=None):
    """Make API request with proper GZIP handling and authentication"""
    if not TEMP_STICK_API_KEY:
        logger.error("TEMP_STICK_API_KEY not found")
        return None
    
    headers = {
        'X-API-Key': TEMP_STICK_API_KEY,
        'Accept-Encoding': 'gzip',
        'Content-Type': 'text/plain',
        'User-Agent': 'FreightPace-TempMonitor/1.0'
    }
    
    try:
        response = requests.get(f'{BASE_URL}{endpoint}', headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        # Handle both GZIP and regular JSON responses
        try:
            # Try to decompress if it's GZIP
            if response.headers.get('content-encoding') == 'gzip':
                content = gzip.decompress(response.content)
                return json.loads(content.decode('utf-8'))
            else:
                # Check if content starts with gzip magic number
                if response.content.startswith(b'\x1f\x8b'):
                    content = gzip.decompress(response.content)
                    return json.loads(content.decode('utf-8'))
                else:
                    return response.json()
        except gzip.BadGzipFile:
            # Not actually gzipped, treat as regular JSON
            return response.json()
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error making API request to {endpoint}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response from {endpoint}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in API request to {endpoint}: {e}")
        return None


def get_sensors():
    """Get list of all Temp Stick sensors"""
    data = make_api_request('/sensors/all')
    if data and data.get('type') == 'success':
        sensors = data.get('data', {}).get('items', [])
        logger.info(f"Retrieved {len(sensors)} sensors from Temp Stick")
        return sensors
    return []


def get_sensor_data(sensor_id, hours=24):
    """Get temperature data for a specific sensor"""
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    params = {
        'start': start_time.isoformat() + 'Z',
        'end': end_time.isoformat() + 'Z'
    }
    
    data = make_api_request(f'/sensors/{sensor_id}/data', params)
    if data:
        logger.info(f"Retrieved data for sensor {sensor_id}")
        return data
    return {}


def get_current_temperatures():
    """Get current temperature readings for all sensors"""
    sensors = get_sensors()
    current_readings = []
    
    # If no sensors found, return empty list with connection status
    if not sensors:
        logger.warning("No sensors retrieved from Temp Stick API - check API connection")
        return []
    
    for sensor in sensors:
        sensor_id = sensor.get('id')
        if not sensor_id:
            continue
            
        # Get recent data (last 2 hours)
        data = get_sensor_data(sensor_id, hours=2)
        readings = data.get('data', [])
        
        if readings:
            # Get the most recent reading
            latest_reading = readings[-1]
            temp_c = latest_reading.get('temperature')  # Temp Stick returns temperature in Celsius
            temp_f = celsius_to_fahrenheit(temp_c)
            
            current_readings.append({
                'sensor_id': sensor_id,
                'name': sensor.get('name', f'Sensor {sensor_id}'),
                'location': sensor.get('location', 'Unknown'),
                'temperature_f': temp_f,
                'temperature_c': temp_c,
                'humidity': latest_reading.get('humidity'),
                'timestamp': latest_reading.get('timestamp'),
                'battery_level': sensor.get('battery_level'),
                'signal_strength': sensor.get('signal_strength'),
                'status': determine_status(temp_f)
            })
    
    return current_readings


def determine_status(temp_f):
    """Determine status based on temperature"""
    if temp_f is None:
        return 'unknown'
    
    # Standard reefer temperature ranges (can be customized)
    if temp_f <= 32:  # Frozen goods
        return 'normal'
    elif temp_f <= 38:  # Refrigerated goods
        return 'normal'
    elif temp_f <= 45:  # Warning range
        return 'warning'
    else:  # Above safe temperature
        return 'critical'


def check_temperature_alerts():
    """Check for temperature violations and generate alerts"""
    current_readings = get_current_temperatures()
    alerts = []
    
    for reading in current_readings:
        temp_f = reading.get('temperature_f')
        if temp_f is None:
            continue
            
        # Check for temperature violations
        if temp_f > 45:  # Critical high temperature
            alerts.append({
                'sensor_id': reading['sensor_id'],
                'sensor_name': reading['name'],
                'type': 'temperature_high',
                'severity': 'critical',
                'message': f"High temperature alert: {temp_f}°F",
                'temperature': temp_f,
                'timestamp': reading['timestamp']
            })
        elif temp_f > 38:  # Warning temperature
            alerts.append({
                'sensor_id': reading['sensor_id'],
                'sensor_name': reading['name'],
                'type': 'temperature_warning',
                'severity': 'warning',
                'message': f"Temperature warning: {temp_f}°F",
                'temperature': temp_f,
                'timestamp': reading['timestamp']
            })
        
        # Check for sensor issues
        battery_level = reading.get('battery_level')
        if battery_level and battery_level < 20:
            alerts.append({
                'sensor_id': reading['sensor_id'],
                'sensor_name': reading['name'],
                'type': 'low_battery',
                'severity': 'warning',
                'message': f"Low battery: {battery_level}%",
                'battery_level': battery_level,
                'timestamp': reading['timestamp']
            })
    
    return alerts