import logging
from kiteconnect import KiteConnect
import os, sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def get_validated(token: str,
                                API_KEY: str) -> bool:
    """
    Checks if the given access token is currently valid by making a lightweight API call.
    Returns True if valid, False otherwise.
    """
    
    logger.info(f"...validating")
    try:
        temp_kc = KiteConnect(api_key=API_KEY) # Use a temporary instance for validation
        temp_kc.set_access_token(token)
        profile = temp_kc.profile() # A lightweight call to check token validity
        logger.info(f"Access token successfully validated for Kite user: {profile.get('user_id')}")
        return True
    except Exception as e:
        logger.warning(f"Access token validation failed: {e}")
        return False
