import requests
import pandas as pd
from setup_info import SWID, ESPN_S2, LEAGUE_ID
import matplotlib.pyplot as plt
import seaborn as sns


def fetch_boxscore_data(url_input):
    req = requests.get(url_input, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()
    return data['schedule'], data['teams']


def create_matchup_data(schedules):
    score_list = []
    for schedule in schedules:
        matchup_period_id = schedule['matchupPeriodId']
        team1_team_id = schedule['away']['teamId']
        team1_total_points = schedule['away']['totalPoints']
        team2_team_id = schedule['home']['teamId']
        team2_total_points = schedule['home']['totalPoints']

        team1_scores = {
            'Matchup_Period': matchup_period_id,
            'Team1_ID': str(team1_team_id),
            'Team1_Points': team1_total_points,
            'Team2_ID': str(team2_team_id),
            'Team2_Points': team2_total_points
        }

        team2_scores = {
            'Matchup_Period': matchup_period_id,
            'Team1_ID': str(team2_team_id),
            'Team1_Points': team2_total_points,
            'Team2_ID': str(team1_team_id),
            'Team2_Points': team1_total_points
        }

        score_list.append(team1_scores)
        score_list.append(team2_scores)
    return pd.DataFrame(score_list)


def create_team_data(team_for_dict):
    team_list = []
    for team in team_for_dict:
        team_id = team['id']
        team_name = team['name']
        team_dict = {
            'Team_ID': str(team_id),
            'Team_Name': team_name
        }
        team_list.append(team_dict)
    return pd.DataFrame(team_list)


###############################################################
# REMOVED temporarily - replace with "ESPNFF-ActualvsOptimal" #
###############################################################
# def get_score_data(url, week_input):
#     week_data = []
#     for week in week_input:
#         req = requests.get(url,
#                            params={'scoringPeriodId': week, 'matchupPeriodId': week},
#                            cookies={"SWID": SWID, "espn_s2": ESPN_S2})
#         data = req.json()
#         data['week'] = week
#         week_data.append(data)
#     return week_data
#
#
#
# # See "ActualvsOptimalScores" for reference
# # Difference is get_score_data contains an additional key for week
# def get_slates(slate_data):
#     result_list = []
#     for data in slate_data:
#         week = data['week']
#         for team in data['teams']:
#             team_id = team['id']
#
#             result_dict = {'Team_ID': team_id,
#                            'Week': week}
#
#             result_list.append(result_dict)
#
#     return result_list
#
# slate_data = get_score_data(matchup_url, weeks)
# slates = get_slates(slate_data)
################################################################

def merge_data(scores_for_df, teams_for_df):
    combine_df = pd.merge(scores_for_df, teams_for_df, left_on='Team1_ID', right_on='Team_ID')
    combine_df = pd.merge(combine_df, teams_for_df, left_on='Team2_ID', right_on='Team_ID')

    combine_df = combine_df.drop(['Team_ID_x', 'Team_ID_y'], axis=1)
    combine_df.rename(columns={'Team_Name_x': 'Team_Name',
                               'Team_Name_y': 'Opp_Name',
                               'Team1_ID': 'Team_ID',
                               'Team1_Points': 'Team_Points',
                               'Team2_ID': 'Opp_ID',
                               'Team2_Points': 'Opp_Points'},
                      inplace=True)

    week_avg = combine_df.groupby(['Matchup_Period']).mean(numeric_only=True, )['Team_Points']
    combine_df = pd.merge(combine_df, week_avg,
                          left_on='Matchup_Period',
                          right_on='Matchup_Period').rename(columns={'Team_Points_x': 'Team_Points',
                                                                     'Team_Points_y': 'Week_Avg'})
    return combine_df


def chart_scores(data, data_year):
    sns.set_theme()
    # sns.relplot(data=data, x='Matchup_Period', y='Team_Points', kind='line', hue='Team_Name')
    # sns.displot(data, x='Team_Points', kind='kde')
    # chart = sns.jointplot(data=data, x='Team_Name', y='Team_Points', kind='boxplot', order='Team_Points')
    chart_order = data.groupby(by=['Team_Name'])['Team_Points'].median().sort_values(ascending=False).index.to_list()
    chart = sns.boxplot(data=data,
                        x='Team_Name',
                        y='Team_Points',
                        order=chart_order).set(
        title=f'Median scores for weeks {min(df["Matchup_Period"])}-{max(df["Matchup_Period"])} {data_year}')
    # chart.plot_joint(sns.histplot)
    # chart.plot_marginals(sns.boxplot)
    plt.show()


if __name__ == '__main__':
    year = 2022
    league_id = LEAGUE_ID
    boxscore_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                   f'leagues/{league_id}?view=mBoxscore'
    matchup_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                  f'leagues/{league_id}?view=mMatchup&view=mMatchupScore'

    weeks = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    posns = ['QB', 'RB', 'WR', 'Flex', 'TE', 'D/ST', 'K']
    struc = [1, 2, 2, 1, 1, 1, 1]
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

    schedule_data, teams = fetch_boxscore_data(boxscore_url)
    score_df = create_matchup_data(schedule_data)
    team_df = create_team_data(teams)
    df = merge_data(score_df, team_df)
    chart_scores(df, year)

    print(df.head().to_string())
