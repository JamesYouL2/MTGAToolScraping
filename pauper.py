import requests
import hashlib
import time
import json
import os
import itertools
import get_db
from datetime import datetime
import pandas as pd

from MTGAToolFunctions import loaddatabase
from MTGAToolFunctions import RankTranslate
from MTGAToolFunctions import GetEvents
import grid_deckdata
import os
from datetime import datetime, timedelta

carddata=loaddatabase()

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


if os.path.exists('rankedconstructed.json'):
    with open('rankedconstructed.json', 'r') as fh:
        matchdata = json.load(fh)
    matchdata_ids = set([x['_id'] for x in matchdata])
else:
    matchdata = []
    matchdata_ids = set()

if 'ii' in locals():
    print(f"Beginning query from 25*{ii}")
    iterlist = range(ii,2000)
else:
    iterlist = range(2000)

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
                    'filter_type': "Ranked Constructed", 
                    #'filter_type': "Events",
                    'filter_event': "Lore_WAR2_Pauper",
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

    with open('rankedconstructed.json', 'w') as fh:
        json.dump(matchdata, fh)


df = pd.DataFrame.from_dict(matchdata)

#########
#Color winrates
#########

df['colors'] = df['colors'].apply(str)

average=df['w'].sum()/df['t'].sum()
colorwinrates = df.groupby('colors')[['w','l','t']].sum().reset_index()
colorwinrates['WinLoss'] = colorwinrates['w']/colorwinrates['t']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['w']) * (colorwinrates['WinLoss'] - average) 

print(colorwinrates.sort_values('ZScore', ascending=False))
#colorwinrates.sort_values('ZScore', ascending=False).to_csv('WARcolorwinrates.tab',sep='\t')

df.rename(columns={'ModuleInstanceData.WinLossGate.CurrentWins':'Wins',
                          'ModuleInstanceData.WinLossGate.CurrentLosses':'Losses'}, 
                 inplace=True)

#########
#MainDecks
#########
maindeck=df['mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])
maindeck=maindeck.merge(carddata)

#list of all decks and main deck cards
MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'name').fillna(0)
MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

MergeMainDeckCards=MainDeckCards.merge(df,right_index=True,left_on='DeckID')

FullMainDeckCards = MergeMainDeckCards.reindex(MergeMainDeckCards.index.repeat(MergeMainDeckCards['t']))

import hdbscan

hdb = hdbscan.HDBSCAN(min_cluster_size=int(np.floor(len(FullMainDeckCards)/30)),prediction_data=True)
hdb.fit(FullMainDeckCards[feature_list])

FullMainDeckCards['hdb'] = pd.Series(hdb.labels_+1, index=FullMainDeckCards.index)
FullMainDeckCards['hdbprob'] = pd.Series(hdb.probabilities_, index=FullMainDeckCards.index)
FullMainDeckCards['hdb'].value_counts()

Final=FullMainDeckCards.drop_duplicates('_id')

MetaList=Final.groupby('hdb')['w','l','t'].sum()

MetaList['WinLoss'] = MetaList['w']/MetaList['t']
MetaList['ZScore'] = 2 * np.sqrt(MetaList['t']) * (MetaList['WinLoss'] - average) 

print(MetaList.sort_values('ZScore',ascending=False))

for i in range(25):
    m1 = (Final['hdb'] == i)
    m2 = Final[m1].mean()
    #print(m2['Jace, Wielder of Mysteries'],i)
    print(m2.nlargest(25),i)