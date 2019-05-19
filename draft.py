import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json
import numpy as np
import pprint

from sklearn.model_selection import train_test_split
from MTGAToolFunctions import loaddatabase
from MTGAToolFunctions import RankTranslate
from MTGAToolFunctions import GetEvents

GetEvents()

S = requests.Session()

url ='https://mtgatool.com/api/'
rslt = S.post(url+"login.php", data={'email':'lastchancexi@yahoo.com', 'password':
                                     '958f83adfb8f6d64fd7f24702f98f8441393d054',
                                     'playername':'', 'playerid':'',
                                     'mtgaversion':'', 'playerid':'',
                                     'version':'', 'reqId':'ABCDEF',
                                     'method':'auth',
                                     'method_path':'/api/login.php'})

token = rslt.json()['token']

carddata = loaddatabase()

data = []
data_ids = set()

decks = {}

# 100 is the number of sets of 25 decklists to retrieve
for ii in range(1000):
    time.sleep(.25) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': -1, 'filter_type': 'Events',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"QuickDraft_WAR_20190510",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    for entry in data_this['result']:
        #if entry['date']<'2019-05-01':
            #break
        time.sleep(.25) # again, give the server a break
        deckid = entry['_id']

        course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        course.raise_for_status()
        assert course.json()['ok'] 

        decks[deckid] = course.json()

        print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame.from_dict(decks,orient='index')

df = json_normalize(inputdf['result'])

print(df['playerRank'].value_counts())

df.rename(columns={'ModuleInstanceData.WinLossGate.CurrentWins':'Wins',
                          'ModuleInstanceData.WinLossGate.CurrentLosses':'Losses'}, 
                 inplace=True)
df['Games'] = df['Wins']+df['Losses']
df['Colors']=df['CourseDeck.colors'].apply(str)

#########
#SPLITTING DATA BY RANK

#df.to_pickle('WARQuickDraft.pkl')
#df=pd.read_pickle('RNAQuickDraft.pkl')

bronzedf = df[df['playerRank']=='Bronze']
df = df[df['playerRank']!='Bronze']
golddf = df[df['playerRank']!='Silver']

average=golddf['Wins'].sum()/golddf['Games'].sum()

#Color winrates
colorwinrates = golddf.groupby('Colors')[['Wins','Losses','Games']].sum().reset_index()
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('1', 'W')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('2', 'U')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('3', 'B')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('4', 'R')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('5', 'G')
colorwinrates['WinLoss'] = colorwinrates['Wins']/colorwinrates['Games']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['Games']) * (colorwinrates['WinLoss'] - average) 

colorwinrates.sort_values('ZScore', ascending=False)
colorwinrates.sort_values('ZScore', ascending=False).to_csv('WARcolorwinrates.tab',sep='\t')


##############
maindeck=golddf['CourseDeck.mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])
maindeck=maindeck.merge(carddata)

#list of all decks and main deck cards
MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'name').fillna(0)
MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

#############
##carddata
#############
cardmaindeck=maindeck.merge(golddf,left_on='DeckID',right_index=True)

cardwinrates = cardmaindeck.loc[maindeck['quantity'] > 0].groupby(['name','rarity'])[['Wins','Losses']].sum().reset_index()
cardwinrates['W/L'] = cardwinrates['Wins']/(cardwinrates['Losses']+cardwinrates['Wins'])

cardwinrates['Games'] = cardwinrates['Wins']+cardwinrates['Losses']

cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='uncommon',cardwinrates['Games'] * (8/3.0), cardwinrates['Games'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='rare',cardwinrates['Games'] * 8, cardwinrates['AdjustedGames'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='mythic',cardwinrates['Games'] * 16, cardwinrates['AdjustedGames'])

cardwinrates['WARC'] = (cardwinrates['W/L'] - .4) * cardwinrates['AdjustedGames']

cardwinrates.loc[cardwinrates['rarity']=='common'].sort_values('WARC', ascending=False).head(10)
cardwinrates.sort_values('WARC', ascending=False).to_csv('WARcardwinrates.tab',sep='\t')

