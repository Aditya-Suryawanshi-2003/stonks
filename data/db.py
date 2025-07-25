# db_module.py

import os, sys
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..')
sys.path.insert(0, project_root)

from questdb.ingress import Sender, TimestampNanos
import psycopg
import requests
import json
# import config


# conn_str = config.CONFIG_GLOBAL_DB.CONN_STRING

# --- QuestDB Client for ingestion ---
# def insert_stock_tick(symbol, price, volume, conf):
#     with Sender.from_conf(conf) as sender:
#         sender.row(
#             'stock_ticks',
#             symbols={'symbol': symbol},
#             columns={'price': price, 'volume': volume},
#             at=TimestampNanos.now()
#         )
#         sender.flush()

# --- psycopg3 CRUD operations ---
# def connect_db(conn_str):
#     return psycopg.connect(conn_str)

# def create_stock_tick(conn_str, symbol, price, volume):
#     with psycopg.connect(conn_str) as conn:
#         with conn.cursor() as cur:
#             cur.execute("INSERT INTO stock_ticks (symbol, price, volume, ts) VALUES (%s, %s, %s, now())", (symbol, price, volume))
#             conn.commit()

# def read_questdb(conn_str, sql):
#     try:
#         logger.info(f"attempting to interact with questdb.. with {conn_str} and {sql}")
#         with psycopg.connect(conn_str, binary=True) as conn:
#             with conn.cursor() as cur:
#                 cur.execute(sql)
#                 return cur.fetchall()
#     except Exception as e:
#         return e

def read_questdb_req(url, params):
    response = requests.get(url = url, params=params)
    data = response.json()
    return json.dumps(data, indent=2)


# def update_stock_tick(conn_str, symbol, ts, price):
#     with psycopg.connect(conn_str) as conn:
#         with conn.cursor() as cur:
#             cur.execute("UPDATE stock_ticks SET price=%s WHERE symbol=%s AND ts=%s", (price, symbol, ts))
#             conn.commit()

# def delete_stock_tick(conn_str, symbol, ts):
#     with psycopg.connect(conn_str) as conn:
#         with conn.cursor() as cur:
#             cur.execute("DELETE FROM stock_ticks WHERE symbol=%s AND ts=%s", (symbol, ts))
#             conn.commit()
