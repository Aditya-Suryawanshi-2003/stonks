import json
import datetime
import os
import logging # Assume logger is configured as in previous snippet

# Assume SESSION_FILE_PATH is defined globally as in the config snippet

def save_session_to_file(data: dict):
    """Saves the session data to a local JSON file."""
    try:
        # Convert datetime objects to string for JSON serialization
        if 'last_updated' in data and isinstance(data['last_updated'], datetime.datetime):
            data['last_updated'] = data['last_updated'].isoformat()
        
        with open(SESSION_FILE_PATH, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Kite session saved to {SESSION_FILE_PATH}")
    except Exception as e:
        logger.error(f"Error saving session to file: {e}")
