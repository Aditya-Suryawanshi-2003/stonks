from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse


import logging
import sys
import os
import webbrowser
from datetime import datetime


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
from data import fetcher
from kiteconnect import KiteConnect
import config
import pyotp

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
                # kc_instance = KiteConnect(api_key=kiteapikey)
                # kc_instance.set_access_token(access_token)

                # data_fetcher = fetcher.FRONTPAGEDATA(kc_instance=kc_instance)
                # params = {
                #     "query": "SELECT timestamp, symbol, price FROM trades limit 5;",  # Replace with your query
                #     "fmt": "json"   # You can also use "csv"
                # }

                # some_data = data_fetcher.test_questdb(url=req_conn_url, params=params)
                # logger.info(f"data fethed: {some_data}")
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
            return RedirectResponse(url=f"/frontpage?message={"new_token_message"}", status_code=303)
            # return HTMLResponse(status_code=200, content="<html><body>New Access Token Available! Try going to /frontpage</body></html>")
        except Exception as e:
            return HTMLResponse(status_code=400, content=f"<html><body>Error: {e}</body></html>")
    
    elif len(request.query_params) == 0:
        logger.info("yes entered!..")
        loaded_session = load_session_from_file.get_file(session_file_name)
        print(loaded_session['timestamp'])
        return HTMLResponse(status_code=200, content=f"<html><body>New Access Since: {loaded_session['timestamp']} </body></html>")


@app.get("/frontpage")
async def frontpage():

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

        data_fetch = fetcher.FRONTPAGEDATA(kc_instance=frontpage_kc_instance)

        # sql = "select * from xyz;"
        sql_query = "SELECT timestamp, symbol, price FROM trades limit 5;"

        # Provide the query parameters
        params = {
            "query": sql_query,
            "fmt": "json"   # You can also use "csv"
        }

        some_data = data_fetch.test_questdb(url=req_conn_url, params=params)

        # print(some_data)
        return PlainTextResponse(f"here is some response and data: {some_data}")
        # return RedirectResponse(url=f"/frontpage?message={"new_token_message"}", 
        #                                                 status_code=303)
        # return HTMLResponse(status_code=200,
        #                     content=f"""
        #                     <html>
        #                         <head><title>Session Valid</title></head>
        #                         <body>
        #                             <h1>Kite Session Already Valid!</h1>
        #                             <p>For user: <b>{loaded_session['kite_user_id']}</b>.</p>
        #                             <p>Data fetching and strategy process initiated in the background.</p>
        #                             <p>some fetched data: {some_data}</p>
        #                             <p>You can close this page now.</p>
                    
        #                         </body>
        #                     </html>
        #                     """)
    


@app.get("/")
async def root_route():
    #basic health check
    return HTMLResponse(status_code=200, content="<html><body>Server Live!</body></html>")



if __name__ == '__main__':
    import uvicorn
    from datetime import datetime
    uvicorn.run("data.daily_auth.auth:app", host="0.0.0.0", port=5005, reload=True)
