from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse


import logging
import sys
import os
import webbrowser
from datetime import datetime
import pandas as pd

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


session_data_cache= {}

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

# callbacks, load_session_from_file, save_session_to_file, validate_access_token
import load_session_from_file, validate_access_token, initiate_kite_login, clear_invalid_session, process_kite_callbacks, save_session_to_file
from data import fetcher, db
from kiteconnect import KiteConnect
import config
import pyotp
import json
from tqdm import tqdm

totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
redirecturi = config.CONFIG_AUTH.REDIRECT_URI
session_file_name = config.CONFIG_AUTH.SESSION_FILE_NAME
conn_string = config.CONFIG_GLOBAL_DB.CONN_STRING
req_conn_url =  config.CONFIG_GLOBAL_DB.REQ_CONN_URL

login_url = f"https://kite.zerodha.com/connect/login?v=3&api_key={kiteapikey}"

# global_kc_instance = KiteConnect(api_key=kiteapikey)

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

# def process_kite_callback():

#     pass

# --- Main Route Handler ---
@app.get("/daily_auth")
async def daily_auth_route_handler(request: Request):
    """
    Main route to handle daily authentication and data fetching.
    Orchestrates the login initiation, callback processing, and data operations.
    Handles login initiation as well as redirects

    if access_token preset, check for validity and reinitiate login if required
    if not present, raise warning. [trigger.py will never send a blank loaded]
    """
    # logger.info(f"{dir(request)}")
    logger.info(f"query_params len: {len(request.query_params)}")

    if "access_token" in request.query_params:
        try:
            access_token = request.query_params.get("access_token")
            # logger.info(f"access_token: {access_token}")
            if not await validate_access_token.get_validated(access_token, kiteapikey):
                logger.warning(f"acces_token: {access_token} not valid")
                initiate_redirect = await initiate_kite_login.initiate(kc_instance= KiteConnect(api_key=kiteapikey))
                logger.info(f"redire with login_url received: {initiate_redirect.headers.get('location')}")
                
                return initiate_redirect
                # return RedirectResponse(url="/frontpage", status_code=302)
                # redirect_url = initiate_redirect.url
            else:
                logger.info("valid access token, reidrect to /frontpage")
                # since access_token is valid, initiate the callbacks to store data here
                # Redirect to /frontpage route instead of returning HTMLResponse here
                return RedirectResponse(url="/frontpage", status_code=302)
                # return HTMLResponse(status_code=200, content="<html><body>New Data Fetched! Try going to /frontpage</body></html>")

                # since access_token is valid, initiate the callbacks to store data here
        except Exception as e:
            logger.warning(f"access token not received {e}")
    
    elif "request_token" in request.query_params:
        try:
            # process callbacks here as login   
            # just store replace request_token with access_token here and save to file
            request_token = request.query_params.get("request_token")
            kc_instance = KiteConnect(api_key=kiteapikey)
            data = kc_instance.generate_session(request_token, api_secret=kiteapisecret)

            data = {
                "access_token": data["access_token"],
                "public_token": data["public_token"],
                "kite_user_id": data["user_id"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            save_session_to_file.save(data, session_file_name)
            
            # return PlainTextResponse("request token exchanged with access_token, and saved")
            return RedirectResponse(url="/data_fetch", status_code=303)
            # return HTMLResponse(status_code=200, content="<html><body>New Access Token Available! Try going to /frontpage</body></html>")
        except Exception as e:
            return HTMLResponse(status_code=400, content=f"<html><body>Error: {e}</body></html>")
    
    elif len(request.query_params) == 0:
        logger.info("yes entered!..")
        loaded_session = load_session_from_file.get_file(session_file_name)
        print(loaded_session['timestamp'])
        return HTMLResponse(status_code=200, content=f"<html><body>New Access Since: {loaded_session['timestamp']} </body></html>")


@app.get("/data_fetch")
async def datafetch():

    loaded_session = load_session_from_file.get_file(session_file_name)
    access_token = loaded_session["access_token"]
    
    valid_resp = await validate_access_token.get_validated(access_token, API_KEY = kiteapikey)
    print(f"response from valid route: {valid_resp}")
    if not valid_resp:
        print("moved to if loop..")
        '''returns invalid token message to the route and asks to initiate login'''

        return HTMLResponse(status_code=401,
                            content=f"""
                            <html>
                                <head><title>Access Token Invalid</title></head>
                                <body>
                                    <h1>Kite Access Token is Invalid!</h1>
                                    <p>Error: {valid_resp}</p>
                                    <p>Please initiate new login, by requesting to /daily_auth</p>
                                    <p>You can close this page now.</p>
                                </body>
                            </html>
                            """)
    else:
        # access_token
        print('moved to else loop..')
        frontpage_kc_instance = KiteConnect(api_key=kiteapikey)
        frontpage_kc_instance.set_access_token(access_token)

        data_fetch = fetcher.AuthData(kc_instance=frontpage_kc_instance)

        holdings = data_fetch.test_holdings()
        all_intruments = data_fetch.test_instruments()
        all_intruments = pd.DataFrame(all_intruments)
        

        nse_eq = all_intruments[(all_intruments['instrument_type'] == 'EQ') &
                                (all_intruments['exchange'] == 'NSE') &
                                (all_intruments['segment'] == 'NSE')
                                ]
        
        # all_symb_list = nse_eq['tradingsymbol'].tolist()
        holdings_list = pd.DataFrame(holdings)['tradingsymbol'].tolist()
        all_nse_eq = nse_eq['tradingsymbol'].tolist()

        # Get HOLDINGS QUOTES
        info, error_symbols = data_fetch.test_nsepy_quotes(holdings_list)
        info_df = pd.DataFrame(info)
        info_df['timestamp'] = pd.to_datetime(info_df['timestamp'])
        info_df['close'] = pd.to_numeric(info_df['close'], errors='coerce').astype(float)
        
        resp = db.insert_dataframe_to_questdb(df=info_df,
                                       table_name='daily_holdings',
                                       timestamp_col='timestamp',
                                       req_conn_url=req_conn_url)
        
        # ADD FOR FETCHING DAILY MARKET DATA HERE
        
        if resp[0]:
            headers = {"message": "process completed. new data fetched and stored"}
            return PlainTextResponse(headers=headers)
        else:
            logger.warning(f"full process not completed :/ {resp[1]}")
            return PlainTextResponse(f"full process not completed :/: {resp[1]}")
    

@app.get("/frontpage")
async def frontpage():

    data_fetcher = fetcher.FRONTPAGEDATA()
    holdings_data = data_fetcher.fetch_holdings()
    logger.info(f"data recvd: {holdings_data.head()}")

    df_data_html = holdings_data.to_html(index=False)
    html_content = f"<h3>this is static data</h3><div style='text-align:center; margin-right:auto; width:50%;'><center>{df_data_html}</center></div>"
    headers = {
        "message": "Landed on /frontpage."
    }
    return HTMLResponse(content=html_content, headers=headers)

@app.get("/")
async def root_route():
    #basic health check
    return HTMLResponse(status_code=200, content="<html><body>Server Live!</body></html>")



if __name__ == '__main__':
    import uvicorn
    from datetime import datetime
    uvicorn.run("data.daily_auth.auth:app", host="0.0.0.0", port=5005, reload=True)
