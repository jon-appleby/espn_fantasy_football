import pandas as pd
import requests
from setup_info import SWID, ESPN_S2, LEAGUE_ID


def get_draft_data(year):
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                  f'leagues/{LEAGUE_ID}?view=mMatchup&view=mDraftDetail'
    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()

    picks = data['draftDetail']['picks']
    for pick in picks:
        team = pick['teamId']
        player_id = pick['playerId']
        player_name = ''
        if player_id in player_map:
            player_name = player_map[player_id]
        round_num = pick['roundId']
        round_pick = pick['roundPickNumber']
        bid_amount = pick['bidAmount']
        keeper_status = pick['keeper']


def get_player_card(year):
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?view=kona_playercard'
    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()


year = 2022
get_draft_data(year)
get_player_card(year)
