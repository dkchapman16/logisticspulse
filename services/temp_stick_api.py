"""
Temp Stick API integration for reefer trailer temperature monitoring
"""
import os
import requests
from datetime import datetime, timedelta
from services.logger import setup_logger

logger = setup_logger(__name__)

TEMP_STICK_API_KEY = os.environ.get('TEMP_STICK_API_KEY')
BASE_URL = 'https://www.tempstick.com/api/v1'


def get_sensors():
    """Get list of all Temp Stick sensors"""
    if not TEMP_STICK_API_KEY:
        logger.error("TEMP_STICK_API_KEY not found")
        return []
    
    try:
        # Try different authentication methods
        headers = {
            'X-API-Key': TEMP_STICK_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.get(f'{BASE_URL}/sensors', headers=headers, timeout=30)
        
        # If that fails, try Bearer token
        if response.status_code == 401 or response.status_code == 403:
            headers = {
                'Authorization': f'Bearer {TEMP_STICK_API_KEY}',
                'Content-Type': 'application/json'
            }
            response = requests.get(f'{BASE_URL}/sensors', headers=headers, timeout=30)
        
        # If still fails, try API key in URL params
        if response.status_code == 401 or response.status_code == 403:
            params = {'api_key': TEMP_STICK_API_KEY}
            response = requests.get(f'{BASE_URL}/sensors', params=params, timeout=30)
        
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Retrieved {len(data.get('sensors', []))} sensors from Temp Stick")
        return data.get('sensors', [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensors from Temp Stick: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_sensors: {e}")
        return []


def get_sensor_data(sensor_id, hours=24):
    """Get temperature data for a specific sensor"""
    if not TEMP_STICK_API_KEY:
        logger.error("TEMP_STICK_API_KEY not found")
        return {}
    
    try:
        headers = {
            'Authorization': f'Bearer {TEMP_STICK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        params = {
            'start': start_time.isoformat() + 'Z',
            'end': end_time.isoformat() + 'Z'
        }
        
        response = requests.get(
            f'{BASE_URL}/sensors/{sensor_id}/data',
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Retrieved data for sensor {sensor_id}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data for sensor {sensor_id}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error in get_sensor_data: {e}")
        return {}


def get_current_temperatures():
    """Get current temperature readings for all sensors"""
    sensors = get_sensors()
    current_readings = []
    
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
            current_readings.append({
                'sensor_id': sensor_id,
                'name': sensor.get('name', f'Sensor {sensor_id}'),
                'location': sensor.get('location', 'Unknown'),
                'temperature_f': latest_reading.get('temperature_f'),
                'temperature_c': latest_reading.get('temperature_c'),
                'humidity': latest_reading.get('humidity'),
                'timestamp': latest_reading.get('timestamp'),
                'battery_level': sensor.get('battery_level'),
                'signal_strength': sensor.get('signal_strength'),
                'status': determine_status(latest_reading.get('temperature_f'))
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