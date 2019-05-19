# cached metadata database retrieval

import json
import requests

cache = {}

def get_db():
    if 'db' not in cache:
        db_rslt = requests.get("https://mtgatool.com/database/database.json")
        db_rslt.raise_for_status()
        db = db_rslt.json()
        cache['db'] = db

    return cache['db']
