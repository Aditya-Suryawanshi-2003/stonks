from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse


import logging
import sys
import os


# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


session_data_cache= {}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# callbacks, load_session_from_file, save_session_to_file, validate_access_token
import load_session_from_file, validate_access_token, initiate_kite_login, clear_invalid_session, process_kite_callbacks
from kiteconnect import KiteConnect
import config
import pyotp

totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
redirecturi = config.CONFIG_AUTH.REDIRECT_URI
session_file_name = config.CONFIG_AUTH.SESSION_FILE_NAME

login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={kiteapikey}"

global_kc_instance = KiteConnect(api_key=kiteapikey)

# Assume all helper functions (load_session_from_file, validate_access_token,
# clear_invalid_session, initiate_kite_login_flow, process_kite_callback,
# perform_daily_data_operations) are defined above.
# Assume session_data_cache and global_kc_instance are defined globally.

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Kite Connect Daily Authenticator & Data Fetcher",
    description="Handles daily Kite Connect authentication and initiates data fetching.",
    version="1.0.0"
)

# AUTH OPERATIONS

def process_kite_callback():

    pass

# --- Main Route Handler ---
@app.get("/daily_auth")
async def daily_auth_route_handler(request: Request):
    """
    Main route to handle daily authentication and data fetching.
    Orchestrates the login initiation, callback processing, and data operations.
    Handles login initiation as well as redirects
    """
    query_params = request.query_params
    request_token = query_params.get("request_token")

    if request_token:
        # This is the callback from Kite Connect


        return await process_kite_callbacks.fetch_data(request_token = request_token, 
                                           error = query_params.get("error"),
                                           API_SECRET = kiteapisecret,
                                           REDIRECT_URI = redirecturi,
                                           kc_instance = global_kc_instance,
                                           session_file_name = session_file_name)
    
        # return PlainTextResponse(f"request token as lohin init received: {request_token}")
    
    else:
        # This is the initial request (e.g., from your 4 PM system command)
        logger.info("Initial request to /daily_auth. Checking for existing valid session.")
        loaded_session = load_session_from_file.get_file(session_file_name)
        print(f"loaded session: {loaded_session}")
        
        if loaded_session and loaded_session != "":
            access_token = loaded_session

            totp = pyotp.TOTP(totpsecret)
            # Get the current OTP
            otp = totp.now()
            print(f"OTP!: {otp}")

            # resp = validate_access_token.get_validated(access_token, API_KEY = kiteapikey)
            if await validate_access_token.get_validated(access_token, API_KEY = kiteapikey):
                print(";ok validated")
        #         # Token is valid, proceed with data fetching and strategy
        #         session_data_cache.update(loaded_session) # Update in-memory cache
        #         global_kc_instance.set_access_token(access_token) # Set for global kc instance
        #         logger.info("Existing access token is valid. Proceeding with data fetching and strategy...")
                
        #         # --- Proceed with data fetching and strategy ---
        #         await perform_daily_data_operations(global_kc_instance)

        #         return HTMLResponse(
        #             status_code=200,
        #             content=f"""
        #             <html>
        #                 <head><title>Session Valid</title></head>
        #                 <body>
        #                     <h1>Kite Session Already Valid!</h1>
        #                     <p>For user: <b>{loaded_session.get('kite_user_id', 'N/A')}</b>.</p>
        #                     <p>Data fetching and strategy process initiated in the background.</p>
        #                     <p>You can close this page now.</p>
        #                     <p>Current Time: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        #                 </body>
        #             </html>
        #             """
        #         )
            else:
                # Token found but invalid/expired, remove it and initiate new login
                logger.warning("Existing access token found but is invalid/expired. Clearing and initiating new login.")
                clear_invalid_session.clear_sessions_file(session_file_name)
                totp = pyotp.TOTP(totpsecret)
                # Get the current OTP
                otp = totp.now()
                print(f"OTP!: {otp}")
                return await initiate_kite_login.initiate(kc_instance= global_kc_instance)
                return PlainTextResponse("ok from 5005/daily_auth")
        else:
            # No valid token found, initiate new login
            logger.info("No valid access token found in file. Initiating new login.")
            clear_invalid_session.clear_sessions_file(session_file_name)
            totp = pyotp.TOTP(totpsecret)
            # Get the current OTP
            otp = totp.now()
            print(f"OTP!: {otp}")
            return await initiate_kite_login.initiate(kc_instance= global_kc_instance)
            return PlainTextResponse("blank or invalid token found")

@app.get("/")
async def root_route():
    #basic health check
    return HTMLResponse(status_code=200, content="<html><body>Server Live!</body></html>")



if __name__ == '__main__':
    import uvicorn
    uvicorn.run("data.daily_auth.auth:app", host="0.0.0.0", port=5005, reload=True)
