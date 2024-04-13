from main.espn_api import fetch_api_data


def fetch_boxscore_data(curr_year, curr_week):
    data = fetch_api_data(views=['mBoxscore'], params={'matchupPeriodId': curr_week}, year=curr_year)
    return data['schedule'], data['teams']


def get_team_ids(team_input) -> dict[int, str]:
    # create team dict
    team_dict = {}
    for team in team_input:
        id = team['id']
        name = team['name']
        team_dict[id] = name

    return team_dict


# def get_team_detail(team_input):
    # for team in team_input:
    #     roster = team['roster']['entries']
    #     print(roster)


schedule_data, team_data = fetch_boxscore_data(2023, 1)
print(team_data)
get_team_ids(team_data)
# get_team_detail(team_data)

# get starting players
