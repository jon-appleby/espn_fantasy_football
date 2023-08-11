import requests
import pandas as pd
import matplotlib.pyplot as plt

slotcodes = {
    0: 'QB', 1: 'QB',
    2: 'RB', 3: 'RB',
    4: 'WR', 5: 'WR',
    6: 'TE', 7: 'TE',
    16: 'D/ST',
    17: 'K',
    20: 'Bench',
    21: 'IR',
    23: 'Flex'
}

swid = "REDACTED_SWID"
espn = "AEBBxiVWbf1QtxwqBpfaDr8GfBKPQ%2FoxsC26BJ4yMs36M9dyqjOIoxnMkLUJTWOwxF9Xw21z%2BJjLRqLNAFJxO9Lt4RG8RwUKqSQzU3BbJn6oMw%2BJleQ9SNIxopGmrDZn2Ts3IQBEvDTdYZ1CzAYPa6vRgWXcK0%2F%2FJV5l9iDlBiNkMbQMFPcrStfIPnoPQ%2FCyn8CPq4RbGJvgG6yEekwRruwd05XapX0dPp%2FGHcV2nDP9qlbuH3nac7mFE%2FI6c%2FHh1N26Vm8SG60sS5YmQSu94vHr "


def get_matchups(league_id, season, week, swid='', espn=''):
    '''
    Pull full JSON of matchup data from ESPN API for a particular week.
    '''

    url = 'https://fantasy.espn.com/apis/v3/games/ffl/seasons/' + \
          str(season) + '/segments/0/leagues/' + str(league_id)

    r = requests.get(url + '?view=mMatchup&view=mMatchupScore',
                     params={'scoringPeriodId': week, 'matchupPeriodId': week},
                     cookies={"SWID": swid, "espn_s2": espn})
    # print(r.json())
    return r.json()


def get_slates(json):
    '''
    Constructs week team slates with slotted position,
    position, and points (actual and ESPN projected),
    given full matchup info (`get_matchups`)
    '''

    slates = {}

    for team in d['teams']:
        slate = []
        for p in team['roster']['entries']:
            # get name
            name = p['playerPoolEntry']['player']['fullName']

            # get actual lineup slot
            slotid = p['lineupSlotId']
            slot = slotcodes[slotid]

            # get projected and actual scores
            act, proj = 0, 0
            for stat in p['playerPoolEntry']['player']['stats']:
                if stat['scoringPeriodId'] != week:
                    continue
                if stat['statSourceId'] == 0:
                    act = stat['appliedTotal']
                elif stat['statSourceId'] == 1:
                    proj = stat['appliedTotal']
                else:
                    print('Error')

            # get type of player
            pos = 'Unk'
            ess = p['playerPoolEntry']['player']['eligibleSlots']
            if 0 in ess:
                pos = 'QB'
            elif 2 in ess:
                pos = 'RB'
            elif 4 in ess:
                pos = 'WR'
            elif 6 in ess:
                pos = 'TE'
            elif 16 in ess:
                pos = 'D/ST'
            elif 17 in ess:
                pos = 'K'

            slate.append([name, slotid, slot, pos, act, proj])
            # print(slate)
        slate = pd.DataFrame(slate, columns=['Name', 'SlotID', 'Slot', 'Pos', 'Actual', 'Proj'])
        slates[team['id']] = slate
    # print(slates)
    return slates


def compute_pts(slates, posns, struc):
    '''
    Given slates (`get_slates`), compute total roster pts:
    actual, optimal, and using ESPN projections

    Parameters
    --------------
    slates : `dict` of `DataFrames`
        (from `get_slates`)
    posns : `list`
        roster positions, e.g. ['QB','RB', 'WR', 'TE']
    struc : `list`
        slots per position, e.g. [1,2,2,1]

    * This is not flexible enough to handle "weird" leagues
    like 6 Flex slots with constraints on # total RB/WR

    Returns
    --------------
    `dict` of `dict`s with actual, ESPN, optimal points
    '''

    data = {}
    for tmid, slate in slates.items():
        pts = {'opts': 0, 'epts': 0, 'apts': 0}

        # ACTUAL STARTERS
        pts['apts'] = slate.query('Slot not in ["Bench", "IR"]').filter(['Actual']).sum().values[0]

        # OPTIMAL and ESPNPROJ STARTERS
        for method, cat in [('Actual', 'opts'), ('Proj', 'epts')]:
            actflex = -100  # actual pts scored by flex
            proflex = -100  # "proj" pts scored by flex
            for pos, num in zip(posns, struc):
                # actual points, sorted by either actual or proj outcome
                t = slate.query('Pos == @pos').sort_values(by=method, ascending=False).filter(['Actual']).values[:, 0]

                # projected points, sorted by either actual or proj outcome
                t2 = slate.query('Pos == @pos').sort_values(by=method, ascending=False).filter(['Proj']).values[:, 0]

                # sum up points
                pts[cat] += t[:num].sum()

                # set the next best as flex
                if pos in ['RB', 'WR', 'TE'] and len(t) > num:
                    fn = t[num] if method == 'Actual' else t2[num]
                    if fn > proflex:
                        actflex = t[num]
                        proflex = fn

            pts[cat] += actflex

        data[tmid] = pts

    return data


def get_teamnames(league_id, season, week, swid='', espn=''):
    url = 'https://fantasy.espn.com/apis/v3/games/ffl/seasons/' + \
          str(season) + '/segments/0/leagues/' + str(league_id)

    r = requests.get(url + '?view=mTeam',
                     params={'scoringPeriodId': week},
                     cookies={"SWID": swid, "espn_s2": espn})
    d = r.json()

    tm_names = {tm['id']: tm['location'].strip() + ' ' + tm['nickname'].strip() \
                for tm in d['teams']}

    return tm_names


league_id = REDACTED_LEAGUE_ID

season = 2022
week = 6
posns = ['QB', 'RB', 'WR', 'Flex', 'TE', 'D/ST', 'K']
struc = [1, 2, 2, 1, 1, 1, 1]

d = get_matchups(league_id, season, week, swid=swid, espn=espn)
slates = get_slates(d)
wdata = compute_pts(slates, posns, struc)
tms = get_teamnames(league_id, season, week, swid=swid, espn=espn)

wdataDf = pd.DataFrame(wdata)
wdataDf = wdataDf.transpose()

# pull team/id (using other script) to join and get team names
url2 = "https://fantasy.espn.com/apis/v3/games/ffl/seasons/2022/segments/0/leagues/REDACTED_LEAGUE_ID"

req = requests.get(url2,
                   cookies={"swid": "REDACTED_SWID",
                            "espn_s2": "AEBBxiVWbf1QtxwqBpfaDr8GfBKPQ%2FoxsC26BJ4yMs36M9dyqjOIoxnMkLUJTWOwxF9Xw21z%2"
                                       "BJjLRqLNAFJxO9Lt4RG8RwUKqSQzU3BbJn6oMw%2BJleQ9SNIxopGmrDZn2Ts3IQBEvDTdYZ1CzAY"
                                       "Pa6vRgWXcK0%2F%2FJV5l9iDlBiNkMbQMFPcrStfIPnoPQ%2FCyn8CPq4RbGJvgG6yEekwRruwd0"
                                       "5XapX0dPp%2FGHcV2nDP9qlbuH3nac7mFE%2FI6c%2FHh1N26Vm8SG60sS5YmQSu94vHr"}
                   )
data = req.json()

dfTeam = [[
    yeet['id'],
    yeet['nickname']]
    for yeet in data['teams']]
dfTeam = pd.DataFrame(dfTeam, columns=['id', 'nickname'])

wdataDf['TeamID'] = range(1, 1 + len(wdataDf))
wdataDf = pd.merge(wdataDf, dfTeam[['id', 'nickname']], left_on='TeamID', right_on='id', how='left')
wdataDf = wdataDf[['TeamID', 'nickname', 'opts', 'apts', 'epts']]
wdataDf['MissedPoints'] = round(wdataDf['opts'] - wdataDf['apts'], 2)
wdataDf['Efficiency'] = (round(wdataDf['apts'] / wdataDf['opts'], 3) * 100)

print(wdataDf)
