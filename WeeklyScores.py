import requests
import pandas as pd
from setup_info import SWID, ESPN_S2, LEAGUE_ID
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


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
# REMOVED temporarily - replace with ActualvsOptimalScores.py #
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
    combine_df.rename(columns={'Team_Name_x': 'team_name',
                               'Team_Name_y': 'opp_name',
                               'Team1_ID': 'team_id',
                               'Team1_Points': 'team_points',
                               'Team2_ID': 'opp_id',
                               'Team2_Points': 'opp_points',
                               'Matchup_Period': 'matchup_period'},
                      inplace=True)

    week_avg = combine_df.groupby(['matchup_period']).mean(numeric_only=True)['team_points']
    combine_df = pd.merge(combine_df, week_avg,
                          left_on='matchup_period',
                          right_on='matchup_period').rename(columns={'team_points_x': 'team_points',
                                                                     'team_points_y': 'week_avg'})

    combine_df['win'] = np.where(combine_df['team_points'] > combine_df['opp_points'], 1, 0)
    combine_df['all_play_win'] = np.where(combine_df['team_points'] > combine_df['week_avg'], 1, 0)

    return combine_df


def chart_scores(data, data_year):
    sns.set_theme(style='darkgrid', palette=None)

    # # create boxplot
    box_chart_order = data.groupby(
        by=['team_name'])['team_points'].median().sort_values(ascending=False).index.to_list()
    sns.boxplot(data=data,
                x='team_name',
                y='team_points',
                order=box_chart_order  # set descending based on median of total score
                ).set(title=f'Median scores for weeks '
                            f'{min(df["matchup_period"])}-{max(df["matchup_period"])} {data_year}')  # set title
    plt.show()

    # scores week by week
    sns.regplot(data=data,
                x='matchup_period',
                y='week_avg').set(title=f'Weekly Avg Score for weeks '
                                        f'{min(df["matchup_period"])}-{max(df["matchup_period"])} {data_year}')
    plt.show()

    # all play win count
    all_play = data.groupby(data['team_name'])['all_play_win'].sum().sort_values(ascending=False).reset_index()
    sns.barplot(data=all_play,
                y='team_name',
                x='all_play_win',
                palette='Spectral').set(title=f'Wins against Weekly Avg for weeks '
                                                           f'{min(df["matchup_period"])}-{max(df["matchup_period"])} '
                                                           f'{data_year}')
    plt.show()

    # team vs opponents
    grid = sns.FacetGrid(data, col='team_name', col_wrap=4)
    grid.map_dataframe(sns.kdeplot, y='opp_points', x='team_points', fill=True, cmap='magma')
    grid.set_axis_labels(y_var='Opponent Points', x_var='Team Points')
    grid.set_titles(col_template='{col_name} Point Density')
    plt.show()


# TODO: highest win-loss margin
# TODO: number of lucky wins or unlucky loses (week score vs week avg)

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
    print(df.head().to_string())

    chart_scores(df, year)

    # df.to_excel('score_data.xlsx')
