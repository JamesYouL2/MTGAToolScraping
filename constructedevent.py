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
df = deckgrid.loc[deckgrid['event']=='QuickDraft_WAR_20190510']
df = df.loc[~df['playerRank'].isin(['Silver','Bronze'])]

print(datetime.fromtimestamp(int(df['date'].min())).strftime('%Y-%m-%d'))

#########
#Color winrates
#########
average=df['wins'].sum()/df['games'].sum()
colorwinrates = df.groupby('colors')[['wins','losses','games']].sum().reset_index()
colorwinrates['WinLoss'] = colorwinrates['wins']/colorwinrates['games']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['games']) * (colorwinrates['WinLoss'] - average) 

colorwinrates.sort_values('ZScore', ascending=False)
colorwinrates.sort_values('ZScore', ascending=False).to_csv('WARcolorwinrates.tab',sep='\t')

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

modeldf = df.merge(MainDeckCards,left_index=True,right_index=True).reset_index(drop=True)
#X = StandardScaler().fit_transform(modeldf[feature_list])
modeldf = modeldf.loc[(modeldf['GoodDeck']==1) | (modeldf['GoodDeck']==0)]
modeldf['GoodDeck'] = modeldf['GoodDeck'].apply(int)

import hdbscan

hdb = hdbscan.HDBSCAN(min_cluster_size=25)
hdb.fit(MainDeckCards[feature_list])

MainDeckCards['hdb'] = pd.Series(hdb.labels_+1, index=MainDeckCards.index)
MainDeckCards['hdb'].value_counts()

for i in range(25):
    m1 = (MainDeckCards['hdb'] == i)
    m2 = MainDeckCards[m1].mean()
    #print(m2['Jace, Wielder of Mysteries'],i)
    print(m2.nlargest(25),i)

MergeMainDeckCards=MainDeckCards.merge(df,right_index=True,left_on='DeckID')

MetaList=MergeMainDeckCards.groupby('hdb')['wins','losses'].sum()

MetaList['WL']=(MetaList['wins'])/(MetaList['wins']+MetaList['losses'])
MetaList['ZScore']=(MetaList['wins']-MetaList['losses'])/np.sqrt(MetaList['wins']+MetaList['losses'])
MetaList.sort_values('ZScore',ascending=False)
