"""
Temperature monitoring routes for Temp Stick integration
"""
from flask import Blueprint, render_template, jsonify, request
from services.temp_stick_api import (
    get_current_temperatures,
    get_sensors,
    get_sensor_data,
    get_temperature_alerts
)
from services.logger import setup_logger

logger = setup_logger(__name__)

temperature_bp = Blueprint('temperature', __name__)


@temperature_bp.route('/')
def index():
    """Show temperature monitoring dashboard"""
    return render_template('temperature.html')


@temperature_bp.route('/api/current')
def get_current_readings():
    """API endpoint to get current temperature readings"""
    try:
        readings = get_current_temperatures()
        return jsonify({
            'success': True,
            'readings': readings,
            'count': len(readings)
        })
    except Exception as e:
        logger.error(f"Error getting current readings: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@temperature_bp.route('/api/sensors')
def get_sensor_list():
    """API endpoint to get list of all sensors"""
    try:
        sensors = get_sensors()
        return jsonify({
            'success': True,
            'sensors': sensors,
            'count': len(sensors)
        })
    except Exception as e:
        logger.error(f"Error getting sensors: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@temperature_bp.route('/api/sensor/<sensor_id>/history')
def get_sensor_history(sensor_id):
    """API endpoint to get temperature history for a specific sensor"""
    try:
        hours = request.args.get('hours', 24, type=int)
        data = get_sensor_data(sensor_id, hours=hours)
        return jsonify({
            'success': True,
            'data': data,
            'sensor_id': sensor_id
        })
    except Exception as e:
        logger.error(f"Error getting sensor history for {sensor_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@temperature_bp.route('/api/alerts')
def get_alerts():
    """API endpoint to get temperature alerts"""
    try:
        alerts = get_temperature_alerts()
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"Error getting temperature alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500