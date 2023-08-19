import json
import pandas as pd
import requests
from setup_info import SWID, ESPN_S2, LEAGUE_ID


def get_draft_data(year):
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?view=mMatchup&view=mDraftDetail'
    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()

    draft = []
    picks = data['draftDetail']['picks']
    for pick in picks:
        pick_details = {'team': pick['teamId'],
                        'player_id': pick['playerId'],
                        'round_num': pick['roundId'],
                        'round_pick': pick['roundPickNumber'],
                        'overall_pick': pick['overallPickNumber']
                        }
        draft.append(pick_details)

    return draft


def get_player_card(year):
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?view=kona_playercard'

    filters = {"players": {"limit": 1500,
                           "sortDraftRanks": {
                               "sortPriority": 100,
                               "sortAsc": True,
                               "value": "STANDARD"
                           }
                           }
               }
    headers = {'x-fantasy-filter': json.dumps(filters)}

    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2}, headers=headers)
    data = req.json()

    players = []
    player_info = data['players']
    for player in player_info:
        ind_player = player['player']
        player_details = {'player_id': ind_player['id'],
                          'first_name': ind_player['firstName'],
                          'last_name': ind_player['lastName']
                          }
        players.append(player_details)

    return players


def combine_draft_player(year):
    draft = pd.DataFrame(get_draft_data(year))
    player = pd.DataFrame(get_player_card(year))

    draft_df = draft.merge(player, how='left', left_on='player_id', right_on='player_id')

    return draft_df


year = 2022
draft = combine_draft_player(year)
