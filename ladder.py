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
for ii in range(50):
    time.sleep(.2) # give the server a break, sleep between queries

    skip = ii * 25

    # do not use any filters - it's apparently a lighter load for the server that way
    result = S.post(url+"get_explore.php",
                    data={'token': token, 'filter_wcc': "", 'filter_wcu': "",
                          'filter_sortdir': 1, 'filter_type': 'Ranked Constructed',
                          'filter_sort':"By Date", 'filter_skip':str(skip),
                          'filter_owned':"false", 'filter_event':"Ladder",
                          "filter_wcr":"", "filter_wcm":"", })

    data_this = result.json()

    unique_ids = set([x['_id'] for x in data_this['result']])

    n_unique = len(unique_ids - data_ids)

    data += data_this['result']

    data_ids = data_ids | unique_ids

    print(f"Added {n_unique} new ids of {len(unique_ids)} retrieved, total {len(data)}")

    # download each deck / match result entry
    #for entry in data_this['result']:
        #time.sleep(.25) # again, give the server a break
        #deckid = entry['_id']

        #course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
        #course.raise_for_status()
        #assert course.json()['ok']

        #decks[deckid] = course.json()

        #print(".", end="", flush=True)

#have to start by converting to pandas df
inputdf = pd.DataFrame(data)
#save pandas df
inputdf.to_pickle('ladder.pkl')
##########
#Load pandas df
inputdf=pd.read_pickle('ladder.pkl')
#########
#Color winrates
#df = json_normalize(inputdf['result'])
#df['Colors']=df['CourseDeck.colors'].apply(str)
#colorwinrates = df.groupby('Colors')[['ModuleInstanceData.WinLossGate.CurrentWins','ModuleInstanceData.WinLossGate.CurrentLosses']].sum().reset_index()
##########
inputdf=inputdf[inputdf['rank'].isin(['Gold', 'Platinum', 'Diamond', 'Mythic'])]

maindeck=inputdf['mainDeck'].apply(json_normalize)
maindeck=pd.concat(maindeck.to_dict(),axis=0)
maindeck.index = maindeck.index.set_names(['DeckID', 'Seq'])
maindeck.reset_index(inplace=True)  
maindeck['id']=pd.to_numeric(maindeck['id'])

MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'id').fillna(0)

#get wins and losses
winloss=inputdf[['w','l']]
winloss['WL']=winloss['w']/(winloss['l']+winloss['w'])

MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

from MTGAToolFunctions import loaddatabase

carddata = loaddatabase()
maindeck=maindeck.merge(carddata)

MainDeckCards=maindeck.pivot_table('quantity', ['DeckID'], 'name').fillna(0)
MainDeckCards = MainDeckCards.astype(int)
feature_list=list(MainDeckCards)

from sklearn.preprocessing import StandardScaler

X = StandardScaler().fit_transform(MainDeckCards)

from sklearn.cluster import KMeans

kmeans = KMeans(n_clusters=10)
kmeans.fit(MainDeckCards[feature_list])
kmeans.predict(MainDeckCards[feature_list])
MainDeckCards['kmeans'] = pd.Series(kmeans.predict(MainDeckCards[feature_list]), index=MainDeckCards.index)

for i in range(10):
    m1 = (MainDeckCards['kmeans'] == i)
    m2 = (MainDeckCards[m1] != 0).all()
    print (list(MainDeckCards.loc[m1,m2]))

from sklearn.cluster import MeanShift
meanshift = MeanShift(bandwidth=2)
meanshift.fit(MainDeckCards)
meanshift.predict(MainDeckCards)
MainDeckCards['meanshift'] = pd.Series(meanshift.predict(MainDeckCards), index=MainDeckCards.index)
MainDeckCards['meanshift'].value_counts()
MainDeckCards=MainDeckCards.drop(columns="meanshift")

from sklearn.cluster import AgglomerativeClustering
aggcluster = AgglomerativeClustering(n_clusters=10)
aggcluster.fit(MainDeckCards[feature_list])

MainDeckCards['aggcluster'] = pd.Series(aggcluster.labels_, index=MainDeckCards.index)
MainDeckCards['aggcluster'].value_counts()

for i in range(10):
    m1 = (MainDeckCards['aggcluster'] == i)
    m2 = (MainDeckCards[m1] != 0).all()
    print (list(MainDeckCards.loc[m1,m2]))

from sklearn.mixture import GaussianMixture

gmm = GaussianMixture(n_components=10).fit(MainDeckCards[feature_list])
MainDeckCards['gmm'] = pd.Series(gmm.predict(MainDeckCards[feature_list]), index=MainDeckCards.index)
MainDeckCards['gmm'].value_counts()

for i in range(10):
    m1 = (MainDeckCards['gmm'] == i)
    m2 = (MainDeckCards[m1] != 0).all()
    print (list(MainDeckCards.loc[m1,m2]))

from sklearn.cluster import DBSCAN
dbscan = DBSCAN(eps=13).fit(MainDeckCards[feature_list])
MainDeckCards['dbscan'] = pd.Series(dbscan.labels_, index=MainDeckCards.index)
MainDeckCards['dbscan'].value_counts()

for i in range(13):
    m1 = (MainDeckCards['dbscan'] == i)
    m2 = (MainDeckCards[m1] != 0).all()
    print (list(MainDeckCards.loc[m1,m2]))