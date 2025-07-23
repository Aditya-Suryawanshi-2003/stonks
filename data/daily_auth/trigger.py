# trigger.py

import requests
import subprocess
import time
import logging
import os
import webbrowser

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
FASTAPI_HOST = "127.0.0.1"
FASTAPI_PORT = 5005
FASTAPI_BASE_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}"
DAILY_AUTH_ENDPOINT = f"{FASTAPI_BASE_URL}/daily_auth"
HEALTH_CHECK_ENDPOINT = f"{FASTAPI_BASE_URL}/" # A simple endpoint to check if server is alive

# Path to your FastAPI main.py relative to the project root
# Assuming trigger.py is in the 'stonks/' directory (project root)
# and main.py is in 'stonks/data/daily_auth/'
FASTAPI_APP_PATH = "data.daily_auth.auth:app" 

# --- Functions ---

def is_server_running(url: str) -> bool:
    """Checks if the FastAPI server is running by attempting a GET request."""
    try:
        logger.info(f"Attempting to connect to server at {url} for health check...")
        response = requests.get(url, timeout=2) # Short timeout for quick check
        # A 200 OK or 404 Not Found (if root isn't defined) indicates the server is alive
        return response.status_code in [200, 404]
    except requests.exceptions.ConnectionError:
        logger.warning("Server is not reachable (ConnectionError).")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Server connection timed out.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during server check: {e}")
        return False

def start_fastapi_server(app_path: str, host: str, port: int):
    """Starts the FastAPI server in a new subprocess."""
    logger.info(f"Server not running. Attempting to start FastAPI server: uvicorn {app_path} --host {host} --port {port}")
    
    # Use subprocess.Popen to run the command in the background
    # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL suppresses output from the server process
    # You might want to remove these for debugging server startup issues.
    server_process = subprocess.Popen(
        ["uvicorn", app_path, "--host", host, "--port", str(port)],
        # stdout=subprocess.DEVNULL,
        # stderr=subprocess.DEVNULL
    )
    logger.info(f"FastAPI server process started with PID: {server_process.pid}")
    return server_process

def send_daily_auth_request(endpoint_url: str):
    """Sends the request to the /daily_auth endpoint."""
    try:
        logger.info(f"Sending request to daily_auth endpoint: {endpoint_url}")

        #FETCHING RESPONSE HERE
        response = requests.get(endpoint_url)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        logger.info(f"Request to /daily_auth successful. Status: {response.status_code}")
        logger.info(f"Response received from /daily_auth:   {response}")
        logger.info(f"login_url from /daily_auth:   {response.url}")

        if len(response.url) > 0:
            logger.info("Detected redirect to Kite login page. Opening browser for manual login.")
            webbrowser.open(response.url) # Open the actual Kite login URL

        else:
            logger.info("Response is not an HTML redirect for login. Check logs for details.")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending request to /daily_auth: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during daily_auth request: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    server_process = None
    try:
        if not is_server_running(HEALTH_CHECK_ENDPOINT):
            logger.info("FastAPI server is not running. Starting it now...")
            server_process = start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT)
            
            # Give the server some time to start up
            logger.info("Giving server 5 seconds to warm up...")
            time.sleep(5) 

            # Verify if server started successfully
            if not is_server_running(HEALTH_CHECK_ENDPOINT):
                logger.error("Failed to start FastAPI server. Aborting daily auth process.")
                if server_process:
                    server_process.terminate()
                exit(1)
            logger.info("FastAPI server appears to be running.")
        else:
            logger.info("FastAPI server is already running.")

        # Server is confirmed to be running, now send the daily_auth request
        send_daily_auth_request(DAILY_AUTH_ENDPOINT)

    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
    finally:
        # If we started the server, ensure it's terminated when this script exits
        if server_process:
            logger.info(f"Terminating FastAPI server process (PID: {server_process.pid})...")
            server_process.terminate()
            server_process.wait(timeout=5) # Wait for it to terminate
            if server_process.poll() is None: # If still running
                logger.warning("FastAPI server process did not terminate gracefully, killing it.")
                server_process.kill()
            logger.info("FastAPI server process terminated.")
