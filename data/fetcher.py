"""
data/fetcher.py
Responsible for fetching asset and strategy data from database or external APIs.
"""




import os, sys
from typing import List, Dict, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)


from data import db

# Placeholder for DB/API connection imports

class AuthData:

    def __init__(self, 
                 kc_instance: object):
        self.init_aleert = 'obj_created'
        self.kc_instance = kc_instance
    
    def test_fetchdaily(self):

        profile = self.kc_instance.profile()
        holdings = self.kc_instance.holdings()
        orders = self.kc_instance.orders()
        all_instruments = self.kc_instance.instruments()

        return profile

class FRONTPAGEDATA:

    def __init__(self, kc_instance: object):
        self.init_alert = 'obj_init'
        self.kc_instance = kc_instance

    def test_kiteapi_call_holdings(self):
        holdings = self.kc_instance.holdings()
        return holdings
    
    def test_questdb(self, sql = None, db_con = None, url = None, params = None):
        # data = db.read_questdb(conn_str = db_con, sql = sql)
        data = db.read_questdb_req(url, params)
        
        return data

        


class DataFetcher:
    """Fetches asset and portfolio strategy data for dashboards and analysis."""

    def __init__(self, db_connection=None):
        # db_connection: connection/session for your database or ORM
        self.db = db_connection

    def fetch_dashboard_data(self, strategies: Optional[List[dict]] = None) -> Dict:
        """
        Fetch all stock/asset data needed for dashboard display.
        Args:
            strategies: List of strategy objects (or dicts) to extract symbols.
        Returns:
            Dictionary keyed by asset symbol, with relevant price/meta data.
        """
        symbols = set()
        if strategies:
            for strat in strategies:
                # Assume each strategy has an 'assets' list with dicts containing 'symbol'
                for asset in strat.assets:
                    symbol = asset.get('symbol') if isinstance(asset, dict) else None
                    if symbol:
                        symbols.add(symbol)

        # Simulate DB/API calls to fetch asset data for each unique symbol
        stock_data = {}
        for sym in symbols:
            stock_data[sym] = self.fetch_single_stock_data(sym)

        return stock_data

    def fetch_single_stock_data(self, symbol: str) -> dict:
        """
        Fetch full historical and metadata for a single asset symbol.
        Placeholder for real database or API integration.
        """
        return {
            'symbol': symbol,
            'price_history': [],  # List of OHLCV dicts or records
            'fundamentals': {},   # Company/ETF fundamentals
            'metadata': {},       # Sector, exchange, etc.
        }



if __name__ == "__main__":

    import requests
    import json

    sql_query = "SELECT timestamp, symbol FROM trades;"

    # Set the QuestDB HTTP endpoint
    url = "http://localhost:9000/exec"

    # Provide the query parameters
    params = {
        "query": sql_query,
        "fmt": "json"   # You can also use "csv"
    }

    # Send GET request
    response = requests.get(url, params=params)

    # Parse JSON response
    data = response.json()
    print(json.dumps(data, indent=2))

    pass