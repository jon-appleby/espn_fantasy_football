import pandas as pd
from main.espn_api import fetch_api_data
from time import sleep

# def get_teams(curr_year, curr_week):
#     data = fetch_api_data(views=['mMatchup'],
#                           params={'matchupPeriodId': curr_week, 'scoringPeriodId': curr_week},
#                           year=curr_year)
#     return data['teams']
#
#
# def get_boxscore(curr_year, curr_week):
#     data = fetch_api_data(views=['mBoxscore'],
#                           params={'matchupPeriodId': curr_week, 'scoringPeriodId': curr_week},
#                           year=curr_year)
#     return data['teams']


def get_player_info(curr_year, curr_week):
    view = ['kona_player_info']
    params = {'scoringPeriodId': curr_week}
    # header = {"x-fantasy-filter": '{"players":{"limit":1500}}'}
    header = {
        'x-fantasy-filter':
            '{"players": '
            '{"limit": "1500", "sortDraftRanks": '
            '{ "sortPriority": "100", '
            '"sortAsc": "true", '
            # '"value": "STANDARD"'
            '"value": "PPR"'
            '}}}'
    }

    data = fetch_api_data(views=view,
                          params=params,
                          year=curr_year,
                          header=header)

    return data


# def get_team_ids(team_input) -> dict[int, str]:
#     # create team dict
#     team_dict = {}
#     for team in team_input:
#         team_id = team['id']
#         name = team['name']
#         team_dict[team_id] = name
#
#     return team_dict
#
#
# def team_detail(team_input):
#     for team in team_input:
#         team_id = team['id']
#         roster = team['roster']['entries']
#         if team_id == 6:
#             for player in roster:
#                 player_detail = player['playerPoolEntry']['player']
#                 player_name = player_detail['fullName']
#                 player_status = player_detail.get('injuryStatus', '')


year = 2023
week = 11

# team_data = get_boxscore(year, week)
# get_team_ids(team_data)

# player_data = get_teams(year, week)
# print(player_data)

# team_detail(player_data)

player_data = get_player_info(year, week)

players = player_data.get('players', [])

injury_status_list = []
for player in players:
    injury_status = player['player'].get('injuryStatus', 'n/a')
    full_name = player['player'].get('fullName', 'n/a')
    player_id = player['player'].get('id', 'n/a')
    injury_status_list.append({'player_id': player_id, 'player_name': full_name, 'injury_status': injury_status})
df = pd.DataFrame(injury_status_list)
ak = df.loc[df['player_name'] == 'Alvin Kamara']
print(ak.head().to_string())
