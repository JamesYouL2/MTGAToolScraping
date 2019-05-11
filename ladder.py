import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json
import os
import numpy as np
import hdbscan

os.chdir("C:/MTGAToolScraping")

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
for ii in range(20):
    time.sleep(.2) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': 1, 'filter_type': 'Ranked Constructed',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"Ladder",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    #for entry in data_this['result']:
        #time.sleep(.25) # again, give the server a break
        #deckid = entry['_id']

        #course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        #course.raise_for_status()
        #assert course.json()['ok']

        #decks[deckid] = course.json()

        #print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame(data)
#save pandas df
inputdf.to_pickle('ladder.pkl')
##########
#Load pandas df
inputdf=pd.read_pickle('ladder.pkl')
#########
#Color winrates
#df = json_normalize(inputdf['result'])
#df['Colors']=df['CourseDeck.colors'].apply(str)
#colorwinrates = df.groupby('Colors')[['ModuleInstanceData.WinLossGate.CurrentWins','ModuleInstanceData.WinLossGate.CurrentLosses']].sum().reset_index()
##########
inputdf.rename(columns={'ModuleInstanceData.WinLossGate.CurrentWins':'Wins',
                          'ModuleInstanceData.WinLossGate.CurrentLosses':'Losses'}, 
                 inplace=True)
inputdf['rank'].value_counts()
inputdf=inputdf[inputdf['rank'].isin(['Gold', 'Platinum', 'Diamond', 'Mythic'])]

maindeck=inputdf['mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])

from MTGAToolFunctions import loaddatabase

carddata = loaddatabase()
maindeck=maindeck.merge(carddata)

array = maindeck[maindeck['set'] == 'War of the Spark']['DeckID'].unique()

maindeck=maindeck.loc[maindeck['DeckID'].isin(array)]

MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'name').fillna(0)
MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

hdb = hdbscan.HDBSCAN(min_cluster_size=3)
hdb.fit(MainDeckCards[feature_list])

MainDeckCards['hdb'] = pd.Series(hdb.labels_+1, index=MainDeckCards.index)
MainDeckCards['hdb'].value_counts()

for i in range(25):
    m1 = (MainDeckCards['hdb'] == i)
    m2 = MainDeckCards[m1].mean()
    #print(m2['Jace, Wielder of Mysteries'],i)
    print(m2.nlargest(25),i)

MergeMainDeckCards=MainDeckCards.merge(inputdf,right_index=True,left_on='DeckID')

MetaList=MergeMainDeckCards.groupby('hdb')['w','l'].sum()

MetaList['WL']=(MetaList['w'])/(MetaList['w']+MetaList['l'])
MetaList['ZScore']=(MetaList['w']-MetaList['l'])/np.sqrt(MetaList['w']+MetaList['l'])
MetaList.sort_values('ZScore',ascending=False)