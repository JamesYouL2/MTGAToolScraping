import pandas
import json
import get_db

ProgressBar = lambda x: x

db = get_db.get_db()

def grid_deckdata(decks, event=None):
    deck_grid = {}
    pb = ProgressBar(len(decks))
    for key,data_ in decks.items():
        deck = data_['result']

        if event is not None and deck['InternalEventName'] != event:
            continue

        if 'WinLossGate' not in deck['ModuleInstanceData']:
            print(f"Skipping deck id {key}")
            continue

        deck_grid[key] = {}

        # array
        deck_grid[key]['colors'] = "".join('wubrg'[x-1] for x in deck['CourseDeck']['colors'])

        deck_grid[key]['id'] = deck['CourseDeck']['id']
        deck_grid[key]['format'] = deck['CourseDeck']['format']

        # array
        #deck_grid[key]['maindeck'] = deck['CourseDeck']['maindeck']
        deck_grid[key]['poolhash'] = deck['playerDeckHash']
        deck_grid[key]['maindeck'] = "\t".join(["{0}{1}".format(card['quantity'],
                                                                db[str(card['id'])]['name'])
                                                for card in deck['CourseDeck']['mainDeck']])
        deck_grid[key]['maindeckct'] = sum(card['quantity'] for card in deck['CourseDeck']['mainDeck'])

        deck_grid[key]['JSONmaindeck'] = deck['CourseDeck']['mainDeck']

        if 'playerRank' in deck:
            deck_grid[key]['playerRank'] = deck['playerRank']
        else:
            # some modes don't have rank
            deck_grid[key]['playerRank'] = None

        deck_grid[key]['land'] = 0
        deck_grid[key]['rare'] = 0
        deck_grid[key]['mythic'] = 0
        deck_grid[key]['uncommon'] = 0
        deck_grid[key]['common'] = 0

        if event is not None:
            for card in deck['CourseDeck']['mainDeck']:
                cn = db[str(card['id'])]['name']
                rarity = db[str(card['id'])]['rarity']
                qty = card['quantity']
                deck_grid[key][cn] = qty
                deck_grid[key][rarity] += qty


        deck_grid[key]['event'] = deck['InternalEventName']

        deck_grid[key]['player'] = deck['player']

        deck_grid[key]['date'] = deck['date']
        deck_grid[key]['wins'] = deck['ModuleInstanceData']['WinLossGate']['CurrentWins']
        deck_grid[key]['losses'] = deck['ModuleInstanceData']['WinLossGate']['CurrentLosses']
        deck_grid[key]['games'] = deck['ModuleInstanceData']['WinLossGate']['CurrentWins'] + deck['ModuleInstanceData']['WinLossGate']['CurrentLosses']

        if deck['ModuleInstanceData']['WinLossGate']['ProcessedMatchIds'] is not None:
            deck_grid[key]['matchids'] = ",".join(deck['ModuleInstanceData']['WinLossGate']['ProcessedMatchIds'])
        else:
            deck_grid[key]['matchids'] = ''

        #pb.update()

    df = pandas.DataFrame.from_dict(deck_grid).T

    return df

def load_deckdata(fn='deckdata.jsonlist', gridded=True, event=None):
    with open(fn, 'r') as fh:
        decks = [json.loads(line) for line in fh]

    deckdict = {row['result']['_id']: row for row in decks}

    if gridded:
        deckgrid = grid_deckdata(deckdict, event=event)
        return deckgrid
    else:
        return deckdict

if __name__ == "__main__":

    deckdict = load_deckdata(gridded=False)

    deckgrid = grid_deckdata(deckdict)

    summary = deckgrid.groupby('event').agg({'event':'count', 'games':'sum', 'wins':'sum'})
    print(summary)