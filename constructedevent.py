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

if os.path.exists('matchdata.json'):
    with open('matchdata.json', 'r') as fh:
        matchdata = json.load(fh)

# 100 is the number of sets of 25 decklists to retrieve
for ii in range(100):
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

#save pandas df
#inputdf.to_pickle('WARLadder.pkl')
##########

#Load pandas df
#inputdf=pd.read_pickle('GRNdraft.pkl')

#########
#Color winrates
df = json_normalize(inputdf['result'])

#########
#MainDecks
#########
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

# Import the model we are using
from sklearn.model_selection import train_test_split
from sklearn.ensemble.partial_dependence import partial_dependence, plot_partial_dependence
from sklearn.ensemble import GradientBoostingRegressor

X_train, X_test, y_train, y_test = train_test_split(modeldf[feature_list], modeldf['GoodDeck'], test_size=0.2)

params = {'n_estimators': 500, 'max_depth': 8, 'min_samples_split': 2,
          'learning_rate': 0.01}

gbr = GradientBoostingRegressor(**params)
gbr.fit(X_train, y_train)
pd.crosstab(y_test, gbr.predict(X_test).round(), rownames=['Actual'], colnames=['Predicted'])

pd.DataFrame({'Variable':X_test.columns,
'Importance':gbr.feature_importances_}).sort_values('Importance', ascending=False)

allpd = {}

for i in range(len(feature_list)-1):
    key, values = partial_dependence(gbr, target_variables=i, X=X_test) 
    allpd.update(dict(zip([feature_list[i]], key.tolist())))

df=pd.DataFrame(dict([ (k,pd.Series(v)) for k,v in allpd.items() ]))

