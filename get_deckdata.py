import requests
import hashlib
import time
import json
import os
import grid_deckdata
import progressbar



# replace this with a progress bar of your choice if you want a progress bar
S = requests.Session()

url ='https://mtgatool.com/api/'
rslt = S.post(url+"login.php", data={'email':'lastchancexi@yahoo.com', 'password':
                                     hashlib.sha1('unreal12'.encode()).hexdigest(),
                                     'playername':'', 'playerid':'',
                                     'mtgaversion':'', 'playerid':'',
                                     'version':'', 'reqId':'FJk2tb',
                                     'method':'auth',
                                     'method_path':'/api/login.php'})
rslt.raise_for_status()
token = rslt.json()['token']

print("Loading match data ...")
if os.path.exists('matchdata.json'):
    with open('matchdata.json', 'r') as fh:
        data = json.load(fh)
else:
    raise IOError("No match list")

print("Loading existing deck data ...")
if os.path.exists('deckdata.jsonlist'):
    with open('deckdata.jsonlist', 'r') as fh:
        decks = [json.loads(line) for line in fh.readlines()]
else:
    decks = []

deckids = [row['result']['_id'] for row in decks]
deckdict = {row['result']['_id']: row for row in decks}


# "bad deck" registry.  In principle, not needed, in practice, there are some deckids that come from the match retrieval system that don't exist
if os.path.exists('bad_decks'):
    with open('bad_decks', 'r') as fh:
        bad_decks = [x.strip() for x in fh.readlines()]
else:
    bad_decks = []


# from matchdata
datadict = {entry['_id']: entry for entry in data}

print("Creating to-do list ...")
skiplist = set(deckids + bad_decks)
todo = [entry['_id'] for entry in data if entry['_id'] not in skiplist]


print()
print("Beginning query series ...")

pb = progressbar.ProgressBar(max_value=len(todo))
i=0
with open('deckdata.jsonlist', 'a') as fh:

    for deckid in todo:
        if deckid not in deckids:
            # download each deck / match result entry

            if deckid in bad_decks:
                continue

            success = False
            while not success:
                # apparently these 'get_course' requests are efficient and cheap on the server side
                #time.sleep(0.5) # again, give the server a break
                try:
                    course = S.post(url+"get_course.php", data={'token': token, 'courseid':deckid})
                    course.raise_for_status()
                    assert course.json()['ok']
                    success = True
                except AssertionError:
                    print(f"Deck id {deckid} not found: {course.json()}")
                    success = False
                    with open('bad_decks','a') as bdfh:
                        bdfh.write(f"{deckid}\n")
                    break
                except Exception as ex:
                    print(f"Exception: {ex}")
                    success = False

            deck = course.json()
            if deck['ok']:
                deckdict[deckid] = deck

                #print(".", end="", flush=True)
                pb.update(i)
                i=i+1

                fh.write(json.dumps(deck) + "\n")
                fh.flush()
        else:
            print(",", end="", flush=True)

#print()
#print("Gridding data ...")
#deckgrid = grid_deckdata.grid_deckdata(deckdict)