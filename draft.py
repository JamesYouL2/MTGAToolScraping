import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json
import numpy as np

from sklearn.model_selection import train_test_split

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
for ii in range(100):
    time.sleep(.5) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': 1, 'filter_type': 'Descending',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"Sealed_WAR_20190422",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    for entry in data_this['result']:
        time.sleep(.2) # again, give the server a break
        deckid = entry['_id']

        course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        course.raise_for_status()
        assert course.json()['ok']

        decks[deckid] = course.json()

        print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame.from_dict(decks,orient='index')

#save pandas df
#inputdf.to_pickle('GRNdraft.pkl')
##########

#Load pandas df
#inputdf=pd.read_pickle('GRNdraft.pkl')

#########
#Color winrates
df = json_normalize(inputdf['result'])
df['Colors']=df['CourseDeck.colors'].apply(str)
colorwinrates = df.groupby('Colors')[['ModuleInstanceData.WinLossGate.CurrentWins','ModuleInstanceData.WinLossGate.CurrentLosses']].sum().reset_index()
##########

df['GoodDeck']=np.where(df['ModuleInstanceData.WinLossGate.CurrentWins']>4.5, 1, .5)
df['GoodDeck']=np.where(df['ModuleInstanceData.WinLossGate.CurrentWins']<1.5, 0, df['GoodDeck'])

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

modeldf = df.merge(MainDeckCards,left_index=True,right_index=True).reset_index(drop=True)
#X = StandardScaler().fit_transform(modeldf[feature_list])
modeldf = modeldf.loc[(modeldf['GoodDeck']==1) | (modeldf['GoodDeck']==0)]
modeldf['GoodDeck'] = modeldf['GoodDeck'].apply(int)

X = modeldf[['CourseDeck.colors','playerRank']]

X = X.merge(pd.get_dummies(X['playerRank']), left_index=True, right_index=True)
X = X.merge(pd.get_dummies(X['CourseDeck.colors'].apply(str)), left_index=True, right_index=True)
X = X.drop(columns=['CourseDeck.colors','playerRank'])

X_train, X_test, y_train, y_test = train_test_split(modeldf[feature_list], modeldf['GoodDeck'], test_size=0.1)

# Import the model we are using
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble.partial_dependence import partial_dependence, plot_partial_dependence
from sklearn.ensemble import GradientBoostingRegressor

rf = RandomForestClassifier(n_estimators=500)

# Train the model on training data
rf.fit(X_train, y_train)

pd.crosstab(y_test, rf.predict(X_test), rownames=['Actual'], colnames=['Predicted'])

params = {'n_estimators': 500, 'max_depth': 4, 'min_samples_split': 2,
          'learning_rate': 0.01, 'loss': 'ls'}

gbr = GradientBoostingRegressor(**params)
gbr.fit(X_train, y_train)
pd.crosstab(y_test, gbr.predict(X_test).round(), rownames=['Actual'], colnames=['Predicted'])

pd.DataFrame({'Variable':X_test.columns,
'Importance':gbr.feature_importances_}).sort_values('Importance', ascending=False)

fig, axs = plot_partial_dependence(gbr, X=X_test, features=['Parhelion Patrol', 'Rubblebelt Boar', 'Hammer Dropper'],
                                       feature_names=feature_list,
                                       n_jobs=1, grid_resolution=10)

allpd = {}

for i in range(len(feature_list)-1):
    key, values = partial_dependence(gbr, target_variables=i, X=X_test) 
    allpd.update(dict(zip([feature_list[i]], key.tolist())))

df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in allpd.items() ]))