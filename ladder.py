import requests
import hashlib
import time
import pandas as pd
from pandas.io.json import json_normalize
import json

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
for ii in range(200):
    time.sleep(1) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': 1, 'filter_type': '',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"QuickDraft_RNA_20190315",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    for entry in data_this['result']:
        time.sleep(.25) # again, give the server a break
        deckid = entry['_id']

        course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        course.raise_for_status()
        assert course.json()['ok']

        decks[deckid] = course.json()

        print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame.from_dict(decks,orient='index')
inputseries=inputdf['result']
#save pandas df
inputdf.to_pickle('inputdf.pkl')
##########
#Load pandas df
inputdf=pd.read_pickle('inputdf.pkl')
#########
#Color winrates
df = json_normalize(inputdf['result'])
df['Colors']=df['CourseDeck.colors'].apply(str)
colorwinrates = df.groupby('Colors')[['ModuleInstanceData.WinLossGate.CurrentWins','ModuleInstanceData.WinLossGate.CurrentLosses']].sum().reset_index()
##########

maindeck=df['CourseDeck.mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])

MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'id').fillna(0)

#get wins and losses
winloss=df[['ModuleInstanceData.WinLossGate.CurrentWins','ModuleInstanceData.WinLossGate.CurrentLosses']]
winloss=winloss.rename(index=int, columns={"ModuleInstanceData.WinLossGate.CurrentWins": "Wins", "ModuleInstanceData.WinLossGate.CurrentLosses": "Losses"})
winloss['WL']=winloss['Wins']/(winloss['Losses']+winloss['Wins'])

wins = pd.DataFrame([winloss.iloc[idx] 
                       for idx in winloss.index 
                       for _ in range(int(winloss.iloc[idx]['Wins']))]).reset_index()
wins['Win'] = 1

loss = pd.DataFrame([winloss.iloc[idx] 
                       for idx in winloss.index 
                       for _ in range(int(winloss.iloc[idx]['Losses']))]).reset_index()

loss['Win'] = 0

y=pd.concat([wins,loss])
y=y[['Win','index']]

MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)
from sklearn.preprocessing import StandardScaler

model=y.merge(MainDeckCards,left_on='index',right_index=True).reset_index(drop=True)
X = StandardScaler().fit_transform(model[feature_list])

X_train, X_test, y_train, y_test = train_test_split(X, model['Win'], test_size=0.25)

#from sklearn.linear_model import LogisticRegression
#logmodel = LogisticRegression()
#logmodel.fit(X_train,y_train)
#pd.crosstab(y_test, logmodel.predict(X_test), rownames=['Actual'], colnames=['Predicted'])

#from sklearn.metrics import classification_report
#print(classification_report(y_test,predictions))

#%matplotlib inline
#import matplotlib.pyplot as plt
#plt.spy(logit)

#from sklearn.decomposition import FactorAnalysis
#factor = FactorAnalysis(1).fit(X)

#df=pd.DataFrame(factor.components_)

# Import the model we are using
from sklearn.ensemble import RandomForestClassifier

# Instantiate model with 1000 decision trees
rf = RandomForestClassifier()

# Train the model on training data
rf.fit(X_train, y_train)

pd.crosstab(y_test, rf.predict(X_test), rownames=['Actual'], colnames=['Predicted'])

x = MainDeckCards

from sklearn.decomposition import PCA

pca = PCA(n_components=2)

principalComponents = pca.fit_transform(x)

principalDf = pd.DataFrame(data = principalComponents
             , columns = ['principal component 1', 'principal component 2'])

finalDf = pd.concat([principalDf, df[['ModuleInstanceData.WinLossGate.CurrentWins']]], axis = 1)

fig = plt.figure(figsize = (8,8))
ax = fig.add_subplot(1,1,1) 
ax.set_xlabel('Principal Component 1', fontsize = 15)
ax.set_ylabel('Principal Component 2', fontsize = 15)
ax.set_title('2 component PCA', fontsize = 20)

targets = [1, 2, 3, 4, 5, 6, 7]
colors = ['red', 'orange', 'yellow', 'blue', 'green', 'purple', 'white']
for target, color in zip(targets,colors):
    indicesToKeep = finalDf['ModuleInstanceData.WinLossGate.CurrentWins'] == target
    ax.scatter(finalDf.loc[indicesToKeep, 'principal component 1']
               , finalDf.loc[indicesToKeep, 'principal component 2']
               , c = color
               , s = 50)
ax.legend(targets)
ax.grid()