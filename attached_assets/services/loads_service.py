import json
import os

LOADS_FILE = "loads.json"

def load_all():
    if not os.path.exists(LOADS_FILE):
        return []
    with open(LOADS_FILE, "r") as f:
        return json.load(f)

def save_all(loads):
    with open(LOADS_FILE, "w") as f:
        json.dump(loads, f, indent=2)

def save_load(new_load):
    loads = load_all()
    loads.append(new_load)
    save_all(loads)

def assign_driver_to_load(load_id, driver_name):
    loads = load_all()
    for load in loads:
        if load.get("id") == load_id:
            load["assigned_driver"] = driver_name
            break
    save_all(loads)

def get_unassigned_loads():
    return [l for l in load_all() if not l.get("assigned_driver")]
