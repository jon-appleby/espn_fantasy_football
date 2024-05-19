from main.espn_api import fetch_api_data


def get_teams(curr_year, curr_week):
    data = fetch_api_data(views=['mMatchup'],
                          params={'matchupPeriodId': curr_week, 'scoringPeriodId': week},
                          year=curr_year)
    return data['teams']


def get_boxscore(curr_year, curr_week):
    data = fetch_api_data(views=['mBoxscore'],
                          params={'matchupPeriodId': curr_week, 'scoringPeriodId': week},
                          year=curr_year)
    return data['teams']


def get_players(curr_year, curr_week):
    data = fetch_api_data(views=['mMatchup','mMatchupScore'],
                          params={'matchupPeriodId': curr_week},
                          year=curr_year)
    return data


def get_team_ids(team_input) -> dict[int, str]:
    # create team dict
    team_dict = {}
    for team in team_input:
        team_id = team['id']
        name = team['name']
        team_dict[team_id] = name

    return team_dict


# def team_detail(team_input):
#     for team in team_input:
#         team_id = team['id']
#         roster = team['roster']['entries']
#         if team_id == 6:
#             for player in roster:
#                 player_detail = player['playerPoolEntry']['player']
#                 player_name = player_detail['fullName']
#                 player_status = player_detail.get('injuryStatus', '')

def player_detail(player_input):
    for matchup in player_input["schedule"]:
        home_team = matchup["home"]["teamId"]
        away_team = matchup["away"]["teamId"]

        for team_id in [home_team, away_team]:
            for player in matchup["teams"][str(team_id)]["roster"]["entries"]:
                player_name = player["playerPoolEntry"]["player"]["fullName"]
                player_injury_status = player["playerPoolEntry"]["player"]["injuryStatus"]

                print(f"{player_name}: {player_injury_status}")


year = 2023
week = 4

team_data = get_boxscore(year, week)
get_team_ids(team_data)

player_data = get_players(year, week)
player_detail(player_data)

# get starting players
