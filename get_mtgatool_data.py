import requests
import hashlib
import time
import json
import os
import itertools
import get_db
from datetime import datetime
import pandas as pd
from MTGAToolFunctions import GetEvents

#GetEvents()

S = requests.Session()

url ='https://mtgatool.com/api/'
rslt = S.post(url+"login.php", data={'email':'lastchancexi@yahoo.com', 'password':
                                     hashlib.sha1('unreal12'.encode()).hexdigest(),
                                     'playername':'', 'playerid':'',
                                     'mtgaversion':'', 'playerid':'',
                                     'version':'', 'reqId':'ABCDEF',
                                     'method':'auth',
                                     'method_path':'/api/login.php'})

rslt.raise_for_status()
token = rslt.json()['token']


#db = get_db.get_db()
#events = db['events']


if os.path.exists('matchdata.json'):
    with open('matchdata.json', 'r') as fh:
        matchdata = json.load(fh)
    matchdata_ids = set([x['_id'] for x in matchdata])
else:
    matchdata = []
    matchdata_ids = set()

if 'ii' in locals():
    print(f"Beginning query from 25*{ii}")
    iterlist = range(ii,500)
else:
    iterlist = range(500)

# examples of how to hack if you want just a single event:
#events_and_filters = (('Sealed_WAR_20190422', 'Events'),)
#events_and_filters = (('CompDraft_WAR_20190425', 'Events'),)

for ii in iterlist:

    skip = ii * 25

    success = False
    while not success:
        time.sleep(2) # give the server a break, sleep between queries
        # do not use any filters - it's apparently a lighter load for the server that way
        query = {'token': token,
                    'filter_wcc': "",
                    'filter_wcu': "",
                    "filter_wcr": "",
                    "filter_wcm": "",
                    'filter_sortdir': -1,
                    'filter_sort': "By Date",
                    #'filter_sort': "By Player",
                    #'filter_sort': "By Wins",
                    'filter_skip': str(skip),
                    'filter_owned': "false",
                    #'filter_type': "Ranked Constructed", 
                    'filter_type': "Events",
                    'filter_event': "",
                }

        try: 
            result = S.post(url+"get_explore.php",
                            data=query)
            result.raise_for_status()
            if 'Fatal error' in result.text:
                print(result.text)
                success = False
            else:
                success = True
        except Exception as ex:
            print(ex)
            success = False

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - matchdata_ids)

    if any(data_this['result']) and n_unique > 0:
        matchdata += [x for x in data_this['result'] if x['_id'] not in matchdata_ids]

        matchdata_ids = matchdata_ids | unique_ids

        print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(matchdata)}.  Last date {data_this['result'][-1]['date']}")
    else:
        print(f"No matches for {query}")
        break

    with open('matchdata.json', 'w') as fh:
        json.dump(matchdata, fh)

##aggregations for analysis
inputpd = pd.DataFrame(matchdata)
inputpd['month']=inputpd['date'].str[:7]
inputpd['day']=inputpd['date'].str[:10]
inputpd.groupby(['event','month']).agg('sum')
inputpd.groupby(['event']).agg('sum')