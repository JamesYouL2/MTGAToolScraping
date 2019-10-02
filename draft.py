import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json
import numpy as np
import pprint
import os

from sklearn.model_selection import train_test_split
from MTGAToolFunctions import loaddatabase
from MTGAToolFunctions import RankTranslate
from MTGAToolFunctions import GetEvents
import grid_deckdata
import datetime

#GetEvents()

print("testing")
with open('deckdata.jsonlist', 'r') as fh:
    test=fh.readlines()
i=0
for line in test:
    try:
        json.loads(line)
        i=i+1
    except:
        print(i)

print("Loading existing deck data ...")
if os.path.exists('deckdata.jsonlist'):
    with open('deckdata.jsonlist', 'r') as fh:
        decks = [json.loads(line) for line in fh.readlines()]

deckdict = {row['result']['_id']: row for row in decks}
deckgrid = grid_deckdata.grid_deckdata(deckdict)

deckgrid['event'].value_counts()
df = deckgrid.loc[deckgrid['event'].str.contains('Draft_M20')]
#df = deckgrid.loc[deckgrid['event'].str.startswith('CompDraft')]
print(df['playerRank'].value_counts())
df = df.loc[~df['playerRank'].isin(['Bronze'])]

datetime.datetime.fromtimestamp(df['date'].min())

df.loc[df['playerRank'].isin(['Bronze'])].groupby('player')['games','wins','losses'].sum().sort_values('games',ascending=False).head(10)

carddata = loaddatabase()

#######
#Rank Winrates
#######
rankwinrates = df.groupby('playerRank')[['wins','losses','games']].sum().reset_index()
rankwinrates['WinLoss'] = rankwinrates['wins']/rankwinrates['games']


#########
#Color winrates
#########
average=df['wins'].sum()/df['games'].sum()
colorwinrates = df.groupby('colors')[['wins','losses','games']].sum().reset_index()
colorwinrates['WinLoss'] = colorwinrates['wins']/colorwinrates['games']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['games']) * (colorwinrates['WinLoss'] - average) 

colorwinrates.sort_values('ZScore', ascending=False)
colorwinrates.sort_values('ZScore', ascending=False).to_csv('M20colorwinrates.tab',sep='\t')

##############
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

#############
##carddata
#############
cardmaindeck=maindeck.merge(df,left_on='DeckID',right_index=True)

cardwinrates = cardmaindeck.loc[maindeck['quantity'] > 0].groupby(['name','rarity'])[['wins','losses','games']].sum().reset_index()
cardwinrates['W/L'] = cardwinrates['wins']/(cardwinrates['losses']+cardwinrates['wins'])

cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='uncommon',cardwinrates['games'] * (8/3.0), cardwinrates['games'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='rare',cardwinrates['games'] * 8, cardwinrates['AdjustedGames'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='mythic',cardwinrates['games'] * 16, cardwinrates['AdjustedGames'])

cardwinrates['WARC'] = (cardwinrates['W/L'] - .4) * cardwinrates['AdjustedGames']

cardwinrates.loc[cardwinrates['rarity']=='common'].sort_values('WARC', ascending=False).head(10)
cardwinrates.sort_values('WARC', ascending=False).to_csv('M20cardwinrates.tab',sep='\t')

