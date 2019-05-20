import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json
import numpy as np

from sklearn.model_selection import train_test_split
from MTGAToolFunctions import loaddatabase
from MTGAToolFunctions import RankTranslate
from MTGAToolFunctions import GetEvents
<<<<<<< HEAD
import hdbscan


GetEvents()

carddata = loaddatabase()

S = requests.Session()

url ='https://mtgatool.com/api/'
rslt = S.post(url+"login.php", data={'email':'lastchancexi@yahoo.com', 'password':
                                     hashlib.sha1('unreal12'.encode()).hexdigest(),
                                     'playername':'', 'playerid':'',
                                     'mtgaversion':'', 'playerid':'',
                                     'version':'', 'reqId':'ABCDEF',
                                     'method':'auth',
                                     'method_path':'/api/login.php'})

token = rslt.json()['token']

data = []
data_ids = set()

decks = {}

# 100 is the number of sets of 25 decklists to retrieve
for ii in range(500):
    time.sleep(.25) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': -1, 'filter_type': 'Events',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"Constructed_Event",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    for entry in data_this['result']:
        if entry['date']<'2019-05-01':
            break
        time.sleep(.25) # again, give the server a break
        deckid = entry['_id']

        course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        course.raise_for_status()
        assert course.json()['ok']

        decks[deckid] = course.json()

        print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame.from_dict(decks,orient='index')
=======
import grid_deckdata
import os
import datetime
>>>>>>> aae664f2fcd0d0559e34ab27c8a2f6b507d82a3a

#save pandas df
#inputdf.to_pickle('WARLadder.pkl')
##########

#Load pandas df
#inputdf=pd.read_pickle('GRNdraft.pkl')

carddata=loaddatabase()

print("Loading existing deck data ...")
if os.path.exists('deckdata.jsonlist'):
    with open('deckdata.jsonlist', 'r') as fh:
        decks = [json.loads(line) for line in fh.readlines()]
        deckdict = {row['result']['_id']: row for row in decks}

deckgrid = grid_deckdata.grid_deckdata(deckdict)
df = deckgrid.loc[deckgrid['event']=='Traditional_Cons_Event']
df = df.loc[~df['playerRank'].isin(['Silver','Bronze'])]

print(datetime.datetime.fromtimestamp(int(df['date'].min())).strftime('%Y-%m-%d'))

#########
#Color winrates
#########
average=df['wins'].sum()/df['games'].sum()
colorwinrates = df.groupby('colors')[['wins','losses','games']].sum().reset_index()
colorwinrates['WinLoss'] = colorwinrates['wins']/colorwinrates['games']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['games']) * (colorwinrates['WinLoss'] - average) 

colorwinrates.sort_values('ZScore', ascending=False)
colorwinrates.sort_values('ZScore', ascending=False).to_csv('WARcolorwinrates.tab',sep='\t')

df.rename(columns={'ModuleInstanceData.WinLossGate.CurrentWins':'Wins',
                          'ModuleInstanceData.WinLossGate.CurrentLosses':'Losses'}, 
                 inplace=True)

df['playerRank'].value_counts()

bronzedf = df[df['playerRank']=='Bronze']
df = df[df['playerRank']!='Bronze']
golddf = df[df['playerRank']!='Silver']

#########
#MainDecks
#########
maindeck=df['JSONmaindeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])
maindeck=maindeck.merge(carddata)

#list of all decks and main deck cards
MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'name').fillna(0)
MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

import hdbscan

hdb = hdbscan.HDBSCAN(min_cluster_size=int(np.floor(len(df)/50)))
hdb.fit(MainDeckCards[feature_list])

MainDeckCards['hdb'] = pd.Series(hdb.labels_+1, index=MainDeckCards.index)
MainDeckCards['hdb'].value_counts()

MergeMainDeckCards=MainDeckCards.merge(df,right_index=True,left_on='DeckID')

MetaList=MergeMainDeckCards.groupby('hdb')['wins','losses'].sum()

MetaList['WL']=(MetaList['wins'])/(MetaList['wins']+MetaList['losses'])
MetaList['ZScore']=(MetaList['wins']-MetaList['losses'])/np.sqrt(MetaList['wins']+MetaList['losses'])
MetaList.sort_values('ZScore',ascending=False)

for i in range(25):
    m1 = (MainDeckCards['hdb'] == i)
    m2 = MainDeckCards[m1].mean()
    #print(m2['Jace, Wielder of Mysteries'],i)
    print(m2.nlargest(25),i)