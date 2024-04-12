from main.espn_api import fetch_api_data


def fetch_boxscore_data(curr_year):
    data = fetch_api_data(views=['mBoxscore'], year=curr_year)
    return data['schedule'], data['teams']


schedule, teams = fetch_boxscore_data(2023)

# create team dict
team_dict = {}
for team in teams:
    id = team['id']
    name = team['name']
    team_dict[id] = name

# get starting players
