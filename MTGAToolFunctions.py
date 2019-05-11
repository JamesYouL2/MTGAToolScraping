# -*- coding: utf-8 -*-
"""
Created on Fri Apr 12 20:44:50 2019

@author: JJYJa
"""

import json
import pandas as pd
import os
from pandas.io.json import json_normalize
import requests

def getdeckids(inputfile, outputfile):  
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    inputdf = pd.read_json(inputfile, lines = True)
    appended_data = []
    
    df = pd.DataFrame
    
    for i in inputdf['result'].iteritems():
        appended_data.append(json_normalize(i[1]))
        
    df = pd.concat(appended_data)
    df = df.reset_index()

    df = df.drop_duplicates("_id")
    
    df["_id"].to_csv(outputfile,index=False)
    
def createdf(inputfile):
    abspath = os.path.abspath(__file__)
    dname = os.path.dirname(abspath)
    os.chdir(dname)
    
    inputdf = pd.read_json(inputfile, lines=True)
    
    df = pd.DataFrame()
    
    ##for i in inputdf['mainDeck'].iteritems():
        ##appended_data.append(json_normalize(i[1]))    

    for index, row in inputdf.iterrows():
        maindeck = json_normalize(row['CourseDeck']['mainDeck'])
        sideboard = json_normalize(row['CourseDeck']['sideboard'])
        if sideboard.empty:
            sideboard['id'] = 0
        df2 = maindeck.merge(sideboard, on='id', how = 'outer')
        df2 = df2.fillna(value=0)
        df2['playerRank']=row['playerRank']
        df2['Wins']=row['ModuleInstanceData']['WinLossGate']['CurrentWins']
        df2['Losses']=row['ModuleInstanceData']['WinLossGate']['CurrentLosses']
        df2['colors'] = ''.join(str(row['CourseDeck']['colors']))
        df2['deckid'] = row['_id']
        df = df.append(df2,ignore_index=True)
        
    df = df.rename(index=str, columns={"quantity_x": "Maindeck", "quantity_y": "sideboard"})

    df['quantity'] = df['Maindeck'] + df['sideboard']

    return df

def loaddatabase(inputfile='database.json'):
    S = requests.Session() 
    db_rslt = S.get("https://mtgatool.com/database/database.json")
    db_rslt.raise_for_status()
    data = db_rslt.json()
    
    l = list(data.values())
    carddata = pd.DataFrame()
    
    for i in l:
        if type(i) == dict and i.get("id") is not None:
            df2 = json_normalize(i)
            carddata = carddata.append(df2,ignore_index=False)
    
    return carddata

    #db_rslt = S.get("https://mtgatool.com/database/database.json")
    #db_rslt.raise_for_status()
    #db = db_rslt.json()
    #events = db['events']

def RankTranslate(row):
    if row['playerRank'] == 'Mythic':
        return 6
    elif row['playerRank'] == 'Diamond':
        return 5 
    elif row['playerRank'] == 'Platinum':
        return 4 
    elif row['playerRank'] == 'Gold':
        return 3
    elif row['playerRank'] == 'Silver':
        return 2
    elif row['playerRank'] == 'Bronze':
        return 1
    else:
        return 0

def GetEvents():
    S = requests.Session()
    db_rslt = S.get("https://mtgatool.com/database/database.json")
    db_rslt.raise_for_status()
    db = db_rslt.json()
    print(db['events'])