# trigger.py

import requests
import subprocess
import time
import logging
import os, sys
import webbrowser
import asyncio
import json

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

import config


FASTAPI_BASE_URL = config.CONFIG_AUTH.FASTAPI_BASE_URL
DAILY_AUTH_ENDPOINT = config.CONFIG_AUTH.DAILY_AUTH_ENDPOINT
HEALTH_CHECK_ENDPOINT = config.CONFIG_AUTH.HEALTH_CHECK_ENDPOINT
FASTAPI_APP_PATH = config.CONFIG_AUTH.FASTAPI_APP_PATH
FASTAPI_HOST = config.CONFIG_AUTH.FASTAPI_HOST
FASTAPI_PORT = str(config.CONFIG_AUTH.FASTAPI_PORT)
SESSION_FILE_NAME = config.CONFIG_AUTH.SESSION_FILE_NAME
# --- Configuration ---
# FASTAPI_HOST = "127.0.0.1"
# FASTAPI_PORT = 5005
# FASTAPI_BASE_URL = f"http://{FASTAPI_HOST}:{FASTAPI_PORT}"
# DAILY_AUTH_ENDPOINT = f"{FASTAPI_BASE_URL}/daily_auth"
# HEALTH_CHECK_ENDPOINT = f"{FASTAPI_BASE_URL}/" # A simple endpoint to check if server is alive

# Path to your FastAPI main.py relative to the project root
# Assuming trigger.py is in the 'stonks/' directory (project root)
# and main.py is in 'stonks/data/daily_auth/'
# FASTAPI_APP_PATH = "data.daily_auth.auth:app" 

import initiate_kite_login, load_session_from_file, save_session_to_file
# --- Functions ---

async def is_server_running(FASTAPI_BASE_URL) -> bool:
    """Checks if the FastAPI server is running by attempting a GET request."""
    try:
        print(f"...Making request to {FASTAPI_BASE_URL}")
        resp = requests.get(FASTAPI_BASE_URL, timeout=10)
        print(f"server response: {resp.status_code}, {resp.content}")
        return True

    except requests.exceptions.ConnectionError:
        logger.warning("Server is not reachable (ConnectionError).")
        return False
    except requests.exceptions.Timeout:
        logger.warning("Server connection timed out.")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during server check: {e}")
        return False


def start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT):
    """Starts the FastAPI server in a new subprocess."""
    logger.info(f"""Server not running. 
    Attempting to start FastAPI server:
    uvicorn {FASTAPI_APP_PATH} --host {FASTAPI_HOST} --port {FASTAPI_PORT}""")
    
    # Use subprocess.Popen to run the command in the background
    # stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL suppresses output from the server process
    # You might want to remove these for debugging server startup issues.
    server_process = subprocess.Popen(
        ["uvicorn", FASTAPI_APP_PATH, "--host", FASTAPI_HOST, "--port", str(FASTAPI_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    logger.info(f"FastAPI server process started with PID: {server_process.pid}")
    return server_process

def send_daily_auth_request(DAILY_AUTH_ENDPOINT: str, FASTAPI_BASE_URL: str, 
                            server_process, SESSION_FILE_NAME: str):
   """
    Sends the request to the /daily_auth endpoint and handles responses,
    including opening a browser for manual login if redirected to Kite.
    """
   session_token = load_session_from_file.get_file(SESSION_FILE_NAME=SESSION_FILE_NAME)
   logger.info(f"session_token: {session_token}")
   try:
        logger.info(f"Sending request to daily_auth endpoint: {DAILY_AUTH_ENDPOINT}")
        
        # requests.get will automatically follow redirects by default (allow_redirects=True)
        # The final response.url will be the Kite login page if redirected,
        # or your FastAPI's page if it returned HTML directly.
        response = requests.get(DAILY_AUTH_ENDPOINT, params= session_token)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        logger.info(f"Request to /daily_auth successful. Final URL: {response.url}, Status: {response.status_code}")
        logger.info(f"Response content (first 500 chars):\n{response.text[:500]}...")

        # --- Logic to open browser based on the final URL and content ---

        # Scenario 1: FastAPI redirected to Kite login page (most common for new login)
        if "kite.zerodha.com/connect/login" in response.url:
            logger.info("Detected redirect to Kite login page. Opening browser for manual login.")
            webbrowser.open(response.url) # Open the actual Kite login URL
        
        # Scenario 2: FastAPI returned its own HTML response (e.g., success, already valid, or error)
        # This happens if your FastAPI endpoint directly renders an HTML page
        # instead of redirecting to Kite.
        elif "text/html" in response.headers.get("Content-Type", ""):
            if "Kite Login Failed: Time Limit Exceeded or Invalid Token" in response.text:
                logger.warning("Kite Login Failed: Manual intervention required (request_token expired).")
                webbrowser.open(DAILY_AUTH_ENDPOINT) # Open your FastAPI's error page
            elif "Kite Login Successful!" in response.text:
                logger.info("Kite Login Successful! Data operations initiated.")
                webbrowser.open(DAILY_AUTH_ENDPOINT) # Open your FastAPI's success page
            elif "Kite Session Already Valid!" in response.text:
                logger.info("Kite Session already valid. Data operations initiated.")
                webbrowser.open(DAILY_AUTH_ENDPOINT) # Open your FastAPI's already valid page
            else:
                logger.info("Received HTML response from FastAPI, but not a known login/status page. Opening for inspection.")
                webbrowser.open(DAILY_AUTH_ENDPOINT) # Open the FastAPI URL to show its HTML
        
        # Scenario 3: Unexpected response type (e.g., JSON if you didn't switch all responses to HTML)
        else:
            logger.info("Response is not an HTML page for login/status, nor a Kite redirect. Check logs and response content.")
   
   except requests.exceptions.HTTPError as e:
    logger.error(f"HTTP Error sending request to /daily_auth: {e.response.status_code} - {e.response.text}")
    if e.response.status_code == 500:
        logger.error("Internal Server Error from FastAPI. Check FastAPI server logs for traceback.")
   except requests.exceptions.RequestException as e:
    logger.error(f"Network/Connection error sending request to /daily_auth: {e}")
   except Exception as e:
    logger.error(f"An unexpected error occurred during daily_auth request: {e}")

# --- Main Logic ---
if __name__ == "__main__":
    # check if session_file_name exists. if does not create a blank file with session_file_name
    # if exists, then below
    SESSION_FILE_PATH = os.path.join(current_dir, f"{SESSION_FILE_NAME}")
    if not os.path.exists(SESSION_FILE_PATH):
        with open(SESSION_FILE_PATH, 'w') as f:
            json.dump({"access_token": "dummy"}, f)
        loaded_session_data = load_session_from_file.get_file(SESSION_FILE_NAME)
    else: # if file already exists
        loaded_session_data = load_session_from_file.get_file(SESSION_FILE_NAME)
    

    logger.info(f"loaded sessions file: {loaded_session_data}")
    # check if server running at root
    if not asyncio.run(is_server_running(FASTAPI_BASE_URL)):
        print(f"Server not running. Invoking server as a subprocess...")
        server_proc = start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT)
        print(f"sending signal {asyncio.run(is_server_running(FASTAPI_BASE_URL))}")

        # perform data fetch operations here
        # start with making a call to /daily_auth with loaded_sesion_data
        # right now, the trigger.py handles root server open/close after checking if live
        # /daily_auth to handle next steps, based on loaded_access_token.
        # if loaded_access_token has valid access_token, then fetch data
        # if not valid access_token, then initiate kite login and store the new loaded access_token
        # 
        response = requests.get(DAILY_AUTH_ENDPOINT, params= loaded_session_data)
        print(f"response: {response.status_code}")
        print(f"sent to: {response.url};")
        print(f"response text/content if exists: {response.content, response.text}")
        print(f"complete auth with OTP in 30s. Server cloases after 30s")


        print("waiting 30s to terminate")
        time.sleep(30)
        server_proc.terminate()
        time.sleep(5)
        print("terminated..")
        pass
    else:
        logger.info(f"Root server running at {FASTAPI_BASE_URL}")
        response = requests.get(DAILY_AUTH_ENDPOINT, params= loaded_session_data)
        print(response.status_code)
        # print(dir(response))
        # options = ['apparent_encoding', 'close', 'connection', 'content', 'cookies', 'elapsed', 'encoding', 'headers', 'history', 
        # 'is_permanent_redirect', 'is_redirect', 'iter_content', 'iter_lines', 'json', 'links', 'next', 'ok', 'raise_for_status',
        # 'raw', 'reason', 'request', 'status_code', 'text', 'url']
        print(f"sent to: {response.url}; Check /daily_auth or /frontpage for latest client-side update")
        # for opt in options:
        #     print(opt, response.options[opt])
        
    # check if server is running at root, by making a request to app_path at host:port.
    # if running alreasy, prepare to make reqeust to /daily_auth
    # if not, then invoke to start the server programatically, and be able to kill the process

    pass

    # server_process = None
    # try:
    #     if not is_server_running(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT):
    #         logger.info("FastAPI server is not running. Starting it now...")
    #         server_process = start_fastapi_server(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT)
            
    #         # Give the server some time to start up
    #         logger.info("Giving server 5 seconds to warm up...")
    #         time.sleep(5) 

    #         # Verify if server started successfully
    #         if not is_server_running(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT):
    #             logger.error("Failed to start FastAPI server. Aborting daily auth process.")
    #             if server_process:
    #                 server_process.terminate()
    #             exit(1)
    #         logger.info("FastAPI server appears to be running.")
    #     else:
    #         server_process = is_server_running(FASTAPI_APP_PATH, FASTAPI_HOST, FASTAPI_PORT)
    #         logger.info(f"FastAPI server is already running at {server_process.pid}")

    #     # Server is confirmed to be running, now send the daily_auth request
    #     send_daily_auth_request(DAILY_AUTH_ENDPOINT, FASTAPI_BASE_URL, 
    #                             server_process, SESSION_FILE_NAME)

    # except KeyboardInterrupt:
    #     logger.info("Process interrupted by user.")
    # finally:
    #     # If we started the server, ensure it's terminated when this script exits
    #     if server_process:
    #         logger.info(f"Terminating FastAPI server process (PID: {server_process.pid})...")
    #         server_process.terminate()
    #         server_process.wait(timeout=5) # Wait for it to terminate
    #         if server_process.poll() is None: # If still running
    #             logger.warning("FastAPI server process did not terminate gracefully, killing it.")
    #             server_process.kill()
    #         logger.info("FastAPI server process terminated.")
