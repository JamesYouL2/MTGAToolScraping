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
import grid_deckdata
import os
from datetime import datetime, timedelta

carddata=loaddatabase()

#save pandas df
#inputdf.to_pickle('WARLadder.pkl')
##########

#Load pandas df
#inputdf=pd.read_pickle('GRNdraft.pkl')

print("Loading existing deck data ...")

if os.path.exists('rankedconstructed.json'):
    with open('rankedconstructed.json', 'r') as fh:
        data = json.load(fh)

# from matchdata
datadict = {entry['_id']: entry for entry in data}
df = pd.DataFrame.from_dict(datadict,orient='index')

df['event'].value_counts()
df['rank'].value_counts()

df = df.loc[df['event']=='Ladder']
df = df.loc[~df['rank'].isin(['Silver','Bronze'])]

df['colors'] = df['colors'].apply(str)

#########
#Color winrates
#########
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

hdb = hdbscan.HDBSCAN(min_cluster_size=int(np.floor(len(FullMainDeckCards)/100)),prediction_data=True)
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