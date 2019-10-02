# cached metadata database retrieval

import json
import requests

cache = {}

def get_db():
    if 'db' not in cache:
        db_rslt = requests.get("https://mtgatool.com/database")
        db_rslt.raise_for_status()
        db = db_rslt.json()
        cache['db'] = db['cards']

    return cache['db']
