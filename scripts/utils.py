"""
Minimal shared utilities for ChatMMA
KISS: Only 5-6 essential functions
"""
import yaml
import json
import os
from datetime import datetime

def load_config():
    """Load config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def load_yaml(filepath):
    """Load any YAML file"""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def save_json(data, filepath):
    """Save data as JSON"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def load_json(filepath):
    """Load JSON file"""
    with open(filepath, 'r') as f:
        return json.load(f)

def log(message, level="INFO"):
    """Simple logging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")

    # Also write to log file if enabled
    config = load_config()
    if config['logging']['log_to_file']:
        log_file = config['logging']['log_file']
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] {level}: {message}\n")

def sanitize_filename(name):
    """Convert event/source name to safe filename"""
    return name.replace(' ', '_').replace('/', '_').replace(':', '')
