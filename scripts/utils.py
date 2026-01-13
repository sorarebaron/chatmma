"""
Minimal shared utilities for ChatMMA
KISS: Only 5-6 essential functions
"""
import yaml
import json
import os
from datetime import datetime

def load_config():
    """Load config.yaml or return defaults if not found"""
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        # Return minimal default config
        return {
            'database': {'path': 'data/chatmma.db'},
            'logging': {'log_to_file': False, 'log_file': 'data/chatmma.log', 'level': 'INFO'}
        }

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
    try:
        config = load_config()
        if config.get('logging', {}).get('log_to_file', False):
            log_file = config['logging']['log_file']
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(f"[{timestamp}] {level}: {message}\n")
    except:
        pass  # Silently fail if config not available

def sanitize_filename(name):
    """Convert event/source name to safe filename"""
    return name.replace(' ', '_').replace('/', '_').replace(':', '')
