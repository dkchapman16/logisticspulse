import os
import logging
import requests
from datetime import datetime, timedelta
import json
from .logger import setup_logger

logger = setup_logger(__name__)

# API Configuration
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
GOOGLE_MAPS_API_URL = "https://maps.googleapis.com/maps/api"

def get_eta(origin, destination, departure_time=None):
    """
    Calculate the estimated time of arrival using Google Maps Distance Matrix API
    
    Args:
        origin (str): Origin in format "lat,lng" or address
        destination (str): Destination in format "lat,lng" or address
        departure_time (int, optional): Departure time in seconds since epoch
    
    Returns:
        dict: ETA data including duration and ETA datetime
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key not configured")
        return None
    
    try:
        # If departure_time is not provided, use current time
        if not departure_time:
            departure_time = 'now'
        
        url = f"{GOOGLE_MAPS_API_URL}/distancematrix/json"
        params = {
            'origins': origin,
            'destinations': destination,
            'mode': 'driving',
            'departure_time': departure_time,
            'traffic_model': 'best_guess',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got valid data
            if data['status'] == 'OK' and data['rows'][0]['elements'][0]['status'] == 'OK':
                # Get duration in traffic
                duration_seconds = data['rows'][0]['elements'][0]['duration_in_traffic']['value']
                
                # Calculate ETA
                now = datetime.utcnow()
                eta = now + timedelta(seconds=duration_seconds)
                
                return {
                    'duration_seconds': duration_seconds,
                    'duration_text': data['rows'][0]['elements'][0]['duration_in_traffic']['text'],
                    'distance_meters': data['rows'][0]['elements'][0]['distance']['value'],
                    'distance_text': data['rows'][0]['elements'][0]['distance']['text'],
                    'eta': eta
                }
            else:
                logger.error(f"Error in Google Maps response: {data['status']}")
                return None
        else:
            logger.error(f"Error getting ETA: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_eta: {str(e)}")
        return None

def get_geocode(address):
    """
    Geocode an address to get lat/lng coordinates
    
    Args:
        address (str): Address to geocode
    
    Returns:
        dict: Location data including lat, lng, and formatted_address
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key not configured")
        return None
    
    try:
        url = f"{GOOGLE_MAPS_API_URL}/geocode/json"
        params = {
            'address': address,
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got valid data
            if data['status'] == 'OK' and len(data['results']) > 0:
                result = data['results'][0]
                location = result['geometry']['location']
                
                return {
                    'lat': location['lat'],
                    'lng': location['lng'],
                    'formatted_address': result['formatted_address']
                }
            else:
                logger.error(f"Error in Google Maps response: {data['status']}")
                return None
        else:
            logger.error(f"Error geocoding address: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_geocode: {str(e)}")
        return None

def get_directions(origin, destination, waypoints=None):
    """
    Get directions between origin and destination
    
    Args:
        origin (str): Origin in format "lat,lng" or address
        destination (str): Destination in format "lat,lng" or address
        waypoints (list, optional): List of waypoints
    
    Returns:
        dict: Directions data including routes
    """
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key not configured")
        return None
    
    try:
        url = f"{GOOGLE_MAPS_API_URL}/directions/json"
        params = {
            'origin': origin,
            'destination': destination,
            'mode': 'driving',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        if waypoints:
            params['waypoints'] = '|'.join(waypoints)
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if we got valid data
            if data['status'] == 'OK':
                return data
            else:
                logger.error(f"Error in Google Maps response: {data['status']}")
                return None
        else:
            logger.error(f"Error getting directions: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Exception in get_directions: {str(e)}")
        return None
