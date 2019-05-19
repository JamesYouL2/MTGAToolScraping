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

print("Loading existing deck data ...")
if os.path.exists('deckdata.jsonlist'):
    with open('deckdata.jsonlist', 'r') as fh:
        decks = [json.loads(line) for line in fh.readlines()]
        deckdict = {row['result']['_id']: row for row in decks}

deckgrid = grid_deckdata.grid_deckdata(deckdict)
df = deckgrid.loc[deckgrid['event']=='QuickDraft_WAR_20190510']
df = df.loc[~df['playerRank'].isin(['Silver','Bronze'])]

datetime.datetime.fromtimestamp(df['date'].min())

carddata = loaddatabase()


#########
#Color winrates
#########
average=df['wins'].sum()/df['games'].sum()
colorwinrates = df.groupby('colors')[['wins','losses','games']].sum().reset_index()
colorwinrates['WinLoss'] = colorwinrates['wins']/colorwinrates['games']

colorwinrates['ZScore'] = 2 * np.sqrt(colorwinrates['games']) * (colorwinrates['WinLoss'] - average) 

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

