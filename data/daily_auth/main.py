# # stonks/data/daily_auth/main.py
# import sys
# import os

# # Add the project root to sys.path so 'config' can be imported correctly
# # ALWAYS DO THIS FOR ALL FILES OF DIFFERENT MODULES FOR PROPER CONFIG PULLS!
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.join(current_dir, '..', '..')
# sys.path.insert(0, project_root)

# # Now, import the config module. This will automatically load the specific .env.
# import config


# totpsecret = config.CONFIG_AUTH.KITE_TOTP_SECRET
# kiteapikey = config.CONFIG_GLOBAL.KITE_API_KEY
# kiteapisecret = config.CONFIG_GLOBAL.KITE_API_SECRET
# redirecturi = config.CONFIG_AUTH.REDIRECT_URI

# totp = pyotp.TOTP(totpsecret)

# # Get the current OTP
# otp = totp.now()
# print(f"OTP!: {otp}")


# # stonks/data/daily_auth/main.py

# import sys
# import os
# from fastapi import FastAPI, Request, HTTPException
# from fastapi.responses import RedirectResponse
# from urllib.parse import urlencode, urlparse, parse_qs
# from kiteconnect import KiteConnect
# import pyotp # Although not directly used for the browser login, good to have for TOTP generation logic if needed elsewhere.
# import logging

# # --- Configure Logging ---
# logging.basicConfig(level=logging.INFO,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# # --- Adjust sys.path to import config from project root ---
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.join(current_dir, '..', '..')
# sys.path.insert(0, project_root)

# # Import your custom config module
# # import config

# # --- Basic Validation of Config ---
# if not all([kiteapikey, kiteapisecret, redirecturi]):
#     logger.error("Missing one or more essential Kite Connect API credentials in .env file.")
#     logger.error(f"API_KEY: {kiteapikey}, API_SECRET: {'*' * len(kiteapisecret) if kiteapisecret else 'N/A'}, REDIRECT_URI: {redirecturi}")
#     sys.exit(1)

# # --- Initialize KiteConnect with API Key ---
# # The API Secret is only used during session generation, not initial KiteConnect object creation.
# kc = KiteConnect(api_key=kiteapikey)

# # --- FastAPI App Initialization ---
# app = FastAPI(
#     title="Kite Connect FastAPI Authenticator",
#     description="A simple FastAPI app to demonstrate Kite Connect OAuth flow and fetch orders.",
#     version="1.0.0"
# )

# # --- Simple In-Memory Session Storage (FOR DEMONSTRATION ONLY) ---
# # WARNING: This is NOT suitable for production environments.
# # In a real application, use proper session management like:
# # from starlette.middleware.sessions import SessionMiddleware
# # app.add_middleware(SessionMiddleware, secret_key="YOUR_VERY_SECRET_KEY_HERE")
# # And then access request.session
# user_sessions = {} # Maps a simple 'session_id' (e.g., user's IP or a generated UUID) to access_token

# @app.get("/")
# async def login_initiate(request: Request):
#     """
#     Root endpoint to initiate the Kite Connect login process.
#     Redirects the user to the Kite login page.
#     """
#     try:
#         # Generate the Kite login URL
#         # The redirect_uri must exactly match what's registered in your Kite Developer Console.
    
#         login_url = kc.login_url()
#         logger.info(f"Generated Kite login URL: {login_url}")
#         return RedirectResponse(url=login_url)
#     except Exception as e:
#         logger.error(f"Error generating login URL: {e}")
#         raise HTTPException(status_code=500, detail=f"Failed to initiate login: {e}")

# @app.get("/api_fetches")
# async def api_fetches_callback(request: Request):
#     """
#     Callback endpoint for Kite Connect after successful user login.
#     Receives the request_token, exchanges it for an access_token,
#     stores the session, and fetches orders.
#     """
#     query_params = request.query_params
#     request_token = query_params.get("request_token")
#     status = query_params.get("status")
#     error = query_params.get("error")

#     if error:
#         logger.error(f"Kite login failed with error: {error}")
#         raise HTTPException(status_code=400, detail=f"Kite login failed: {error}")

#     if not request_token:
#         logger.warning("No request_token received in callback.")
#         raise HTTPException(status_code=400, detail="Missing request_token in callback.")

#     logger.info(f"Received request_token: {request_token}")

#     try:
#         # Exchange the request_token for an access_token
#         # The API_SECRET is required here.
#         data = kc.generate_session(request_token, api_secret=kiteapisecret)
#         access_token = data["access_token"]
#         public_token = data["public_token"] # Also returned, can be useful
#         user_id = data["user_id"] # User ID from Kite

#         logger.info(f"Successfully generated access_token for user: {user_id}")
#         logger.debug(f"Access Token: {access_token}") # Be careful logging sensitive info

#         # --- Store access_token in our mock session ---
#         # In a real app, you'd associate this with a proper user session.
#         # For this demo, we'll use the user_id as a simple key.
#         user_sessions[user_id] = access_token
#         logger.info(f"Access token stored for user: {user_id}")

#         # --- Set the access_token for the KiteConnect instance ---
#         kc.set_access_token(access_token)
#         logger.info("KiteConnect instance updated with access token.")

#         # --- Make an API call to fetch orders ---
#         logger.info(f"Attempting to fetch orders for user: {user_id}")
#         orders = kc.orders()
#         holdings = kc.holdings()
#         profile = kc.profile()
#         logger.info(f"Successfully fetched {len(orders)} orders.")

#         return {
#             "message": "Kite Connect session established and orders fetched!",
#             "user_id": user_id,
#             "access_token_stored": True, # Indicate that it's stored
#             "orders_count": len(orders),
#             "sample_orders": orders[:5], # Return first 5 orders as a sample
#             "holdings": holdings,
#             "profile": profile
#         }

#     except Exception as e:
#         logger.error(f"Error during access token generation or order fetch: {e}", exc_info=True)
#         raise HTTPException(status_code=500, detail=f"Authentication or API call failed: {e}")



# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=5005, reload=True)


