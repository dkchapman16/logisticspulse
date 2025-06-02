import json
import os

def load_json(filename):
    """Load data from a JSON file, return empty list if file doesn't exist"""
    if not os.path.exists(filename):
        return []
    
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_json(filename, data):
    """Save data to a JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)