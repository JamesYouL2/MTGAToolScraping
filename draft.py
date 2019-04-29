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

S = requests.Session()

db_rslt = S.get("https://mtgatool.com/database/database.json")
db_rslt.raise_for_status()
db = db_rslt.json()
events = db['events']


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
for ii in range(100):
    time.sleep(1) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': -1, 'filter_type': 'Events',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"CompDraft_RNA_20190117",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    for entry in data_this['result']:
        time.sleep(.5) # again, give the server a break
        deckid = entry['_id']

        course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        course.raise_for_status()
        assert course.json()['ok'] 

        decks[deckid] = course.json()

        print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame.from_dict(decks,orient='index')
df = json_normalize(inputdf['result'])

#########
#SPLITTING DATA BY RANK

#df.to_pickle('RNATraDraft.pkl')
#df=pd.read_pickle('RNATraDraft.pkl')
carddata = loaddatabase()


print(df['playerRank'].value_counts())

df.rename(columns={'ModuleInstanceData.WinLossGate.CurrentWins':'Wins',
                          'ModuleInstanceData.WinLossGate.CurrentLosses':'Losses'}, 
                 inplace=True)

df['Games'] = df['Wins']+df['Losses']

bronzedf = df[df['playerRank']=='Bronze']
df = df[df['playerRank']!='Bronze']
golddf = df[df['playerRank']!='Silver']
##########
maindeck=golddf['CourseDeck.mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])
maindeck=maindeck.merge(carddata)

goodpct=(maindeck.groupby('name')['quantity'].sum()/maindeck['quantity'].sum())
goodpct=goodpct.rename('good')

maindeck=bronzedf['CourseDeck.mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])
maindeck=maindeck.merge(carddata)
badpct=(maindeck.groupby('name')['quantity'].sum()/maindeck['quantity'].sum())
badpct=badpct.rename('bad')

playrate=pd.concat([goodpct,badpct],axis=1)

playrate['goodminusbad']=playrate['good']-playrate['bad']

#########################
##Color Winrates
golddf['Colors']=golddf['CourseDeck.colors'].apply(str)
colorwinrates = golddf.groupby('Colors')[['Wins','Losses']].sum().reset_index()

colorwinrates['WinLoss'] = colorwinrates['Wins']/(colorwinrates['Wins']+colorwinrates['Losses'])
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('1', 'W')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('2', 'U')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('3', 'B')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('4', 'R')
colorwinrates['Colors'] = colorwinrates['Colors'].str.replace('5', 'G')

colorwinrates['Games'] = colorwinrates['Wins']+colorwinrates['Losses']
colorwinrates['zscore'] = colorwinrates['Games']* (colorwinrates['WinLoss'] - .5) / (.5 * np.sqrt(colorwinrates['Games']))

colorwinrates.sort_values('zscore', ascending=False)
colorwinrates.sort_values('zscore', ascending=False).to_csv('colorwinrates.tab',sep='\t')
##########
df['ModuleInstanceData.WinLossGate.CurrentWins'].value_counts()

df['GoodDeck']=np.where(df['Wins']>2.5, 1, .5)
df['GoodDeck']=np.where(df['Wins']<1.5, 0, df['GoodDeck'])

from MTGAToolFunctions import loaddatabase
carddata = loaddatabase()

maindeck=df['CourseDeck.mainDeck'].apply(json_normalize)
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

cardwinrates = cardmaindeck.loc[maindeck['quantity'] > 0].groupby(['name','rarity'])[['Wins','Losses']].sum().reset_index()
cardwinrates = cardwinrates.loc[cardwinrates['rarity']!='land']
cardwinrates['W/L'] = cardwinrates['Wins']/(cardwinrates['Losses']+cardwinrates['Wins'])

cardwinrates['Games'] = cardwinrates['Wins']+cardwinrates['Losses']

cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='uncommon',cardwinrates['Games'] * (8/3.0), cardwinrates['Games'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='rare',cardwinrates['Games'] * 8, cardwinrates['AdjustedGames'])
cardwinrates['AdjustedGames'] = np.where(cardwinrates['rarity']=='mythic',cardwinrates['Games'] * 16, cardwinrates['AdjustedGames'])

cardwinrates['WARC'] = (cardwinrates['W/L'] - .4) * cardwinrates['AdjustedGames']

cardwinrates.sort_values('WARC', ascending=False).to_csv('cardwinrates.tab',sep='\t')

####
#ARCHETYPE ANALYSIS
####
import hdbscan
hdb = hdbscan.HDBSCAN(min_cluster_size=25)
hdb.fit(MainDeckCards[feature_list])

MainDeckCards['hdb'] = pd.Series(hdb.labels_+1, index=MainDeckCards.index)
MainDeckCards['hdb'].value_counts()

mergedf=MainDeckCards.join(df)
mergedf['Colors']=mergedf['CourseDeck.colors'].apply(str)

hdbcolors=mergedf[['Wins','Losses','Games','hdb','Colors']].groupby(['hdb','Colors']).agg('sum')
hdbvalues=hdbcolors.groupby('hdb').agg('sum')
hdbvalues['zscore']=(hdbvalues['Wins']-hdbvalues['Losses'])/np.sqrt(hdbvalues['Games'])

for i in range(6):
    m1 = (MainDeckCards['hdb'] == i)
    m2 = MainDeckCards[m1].mean()
    print(m2.nlargest(10), i)

############
#Modeling
############
modeldf = df.merge(MainDeckCards,left_index=True,right_index=True).reset_index(drop=True)
#X = StandardScaler().fit_transform(modeldf[feature_list])

# Import the model we are using
from sklearn.model_selection import train_test_split
from sklearn.ensemble.partial_dependence import partial_dependence, plot_partial_dependence
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.grid_search import GridSearchCV   #Perforing grid search
from sklearn.grid_search import RandomizedSearchCV   #Perforing grid search
from sklearn.ensemble import RandomForestClassifier

X_train, X_test, y_train, y_test = train_test_split(modeldf[feature_list], modeldf['Wins'], test_size=0.2)

parameters = {
    "learning_rate": [0.001, 0.01, 0.025],
    "min_samples_split": [2, 3, 4],
    "min_samples_leaf": [2, 3, 4],
    "max_depth":[3,5,8],
    "max_features":["log2",None],
    "criterion": ["friedman_mse"],
    "subsample":[0.8],
    "n_estimators":[500]
    }

rf = RandomForestClassifier(n_estimators=500)

# Train the model on training data
rf.fit(X_train, y_train)

pd.crosstab(y_test, rf.predict(X_test), rownames=['Actual'], colnames=['Predicted'])

clf = GridSearchCV(GradientBoostingRegressor(), parameters, cv=3, n_jobs=-1)
clf.fit(X_train, y_train)
print(clf.score(X_train, y_train))
print(clf.best_params_)

gbr = GradientBoostingRegressor(**clf.best_params_)
gbr.fit(X_train, y_train)
pd.crosstab(y_test, gbr.predict(X_test).round(), rownames=['Actual'], colnames=['Predicted'])

pd.DataFrame({'Variable':X_test.columns,
'Importance':gbr.feature_importances_}).sort_values('Importance', ascending=False)

allpd = {}

for i in range(len(feature_list)-1):
    key, values = partial_dependence(gbr, target_variables=i, X=X_test) 
    allpd.update(dict(zip([feature_list[i]], key.tolist())))

df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in allpd.items() ]))

