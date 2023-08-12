import requests
import pandas as pd
from setup_info import SWID, ESPN_S2, LEAGUE_ID
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import matplotlib.colors as mcolors


def fetch_boxscore_data(url):
    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()
    return data['schedule'], data['teams']


def get_draftpos_rank(url):
    req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
    data = req.json()

    # iterate through the list and append to dict using index + 1 as team ID
    order = data['settings']['draftSettings']['pickOrder']
    pick_order = []
    for index, pos in enumerate(order):
        index += 1
        pick_order.append({'team_id': str(pos), 'draft_pos': index})

    # iterate thru list of teams and get rank + team id
    rank_list = []
    teams = data['teams']
    for team in teams:
        rank = team['rankCalculatedFinal']
        team_id = team['id']
        rank_list.append({'rank': rank, 'team_id': str(team_id)})

    return pd.DataFrame(pick_order), pd.DataFrame(rank_list)


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

def merge_data(scores_for_df, teams_for_df, draft_for_df, rank_for_df):
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

    combine_df = pd.merge(combine_df, draft_for_df, left_on='team_id', right_on='team_id')
    combine_df = pd.merge(combine_df, rank_for_df, left_on='team_id', right_on='team_id')

    week_avg = combine_df.groupby(['matchup_period']).mean(numeric_only=True)['team_points']
    combine_df = pd.merge(combine_df, week_avg,
                          left_on='matchup_period',
                          right_on='matchup_period').rename(columns={'team_points_x': 'team_points',
                                                                     'team_points_y': 'week_avg'})

    combine_df['win'] = np.where(combine_df['team_points'] > combine_df['opp_points'], 1, 0)
    combine_df['all_play_win'] = np.where(combine_df['team_points'] > combine_df['week_avg'], 1, 0)
    combine_df['draft_rank_diff'] = combine_df['draft_pos'] - combine_df['rank']

    return combine_df


def chart_draft_pos_rank(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # compare draft pos to rank
    pos_rank = sns.regplot(data=data,
                           x='draft_pos',
                           y='rank',
                           robust=True)
    pos_rank.invert_yaxis()
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def chart_draft_vs_final(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # visualize where each player moved through the year from draft to final rank
    diff_data = data.groupby(by=['team_name',
                                 'draft_pos'])['draft_rank_diff'].min().reset_index().sort_values(by=['draft_pos'])
    color_map = mcolors.LinearSegmentedColormap.from_list("CustomMap", ['#d4382c', '#deaa3a', '#0fa32c'])
    min_diff = min(diff_data['draft_rank_diff'])
    max_diff = max(diff_data['draft_rank_diff'])
    midpoint = 0
    norm = mcolors.TwoSlopeNorm(vmin=min_diff, vcenter=midpoint, vmax=max_diff)
    sns.barplot(data=diff_data,
                x='draft_rank_diff',
                y='team_name',
                palette=color_map(norm(diff_data['draft_rank_diff'])))
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def chart_week_avg(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # scores week by week
    sns.regplot(data=data,
                x='matchup_period',
                y='week_avg').set(title=f'Weekly Avg Score for weeks '
                                        f'{min(data["matchup_period"])}-{max(data["matchup_period"])}')
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def chart_all_play(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # all play win count
    all_play = data.groupby(data['team_name'])['all_play_win'].sum().sort_values(ascending=False).reset_index()
    sns.barplot(data=all_play,
                y='team_name',
                x='all_play_win',
                palette='crest').set(title=f'Wins against Weekly Avg for weeks '
                                           f'{min(data["matchup_period"])}-{max(data["matchup_period"])}')
    plt.tight_layout()
    if path:
        plt.savefig(path)
    plt.show()


def chart_team_median(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # create boxplot
    box_chart_order = data.groupby(
        by=['team_name'])['team_points'].median().sort_values(ascending=False).index.to_list()
    sns.boxplot(data=data,
                x='team_name',
                y='team_points',
                order=box_chart_order  # set descending based on median of total score
                ).set(title=f'Median scores for weeks '
                            f'{min(data["matchup_period"])}-{max(data["matchup_period"])}')  # set title
    plt.xticks(rotation=90)
    label_y = 50  # Adjust this value to position the label
    for team_name in box_chart_order:
        rank = data[data['team_name'] == team_name]['rank'].values[0]
        plt.text(box_chart_order.index(team_name), label_y,
                 rank, ha='center', va='bottom')
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def chart_team_opp_density(data, path=None, week=17):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] <= week]
    # team vs opponents
    grid = sns.FacetGrid(data, col='team_name', col_wrap=4)
    grid.map_dataframe(sns.kdeplot, y='opp_points', x='team_points', fill=True, cmap='magma')
    grid.set_axis_labels(y_var='Opponent Points', x_var='Team Points')
    grid.set_titles(col_template='{col_name} Point Density')
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


if __name__ == '__main__':
    year = 2022
    league_id = LEAGUE_ID
    boxscore_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                   f'leagues/{league_id}?view=mBoxscore'
    matchup_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                  f'leagues/{league_id}?view=mMatchup&view=mMatchupScore'
    # use to get rankCalculatedFinal
    scoreboard_settings_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                              f'leagues/{league_id}?view=mMatchup&view=mScoreboard&view=mSettings'

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

    # get data and create df
    schedule_data, teams = fetch_boxscore_data(boxscore_url)
    draft_pos, rank_df = get_draftpos_rank(scoreboard_settings_url)
    score_df = create_matchup_data(schedule_data)
    team_df = create_team_data(teams)

    df = merge_data(score_df, team_df, draft_pos, rank_df)
    # df.to_excel('/outputs/score_data.xlsx')
    # print(df.head().to_string())
    # print(df.info())
    # print(df.corr(numeric_only=True).to_string())

    week_max = 14  # set a max week (e.g. use 14 to only see regular season)
    chart_draft_pos_rank(df, './outputs/1pos to rank.png', week_max)
    chart_draft_vs_final(df, './outputs/2diff draft to final.png', week_max)
    chart_week_avg(df, './outputs/3weekly_avg_scores.png', week_max)
    chart_all_play(df, './outputs/4wins_against_week_avg.png', week_max)
    chart_team_median(df, './outputs/5median_scores.png', week_max)
    chart_team_opp_density(df, './outputs/6score_against_opp_density.png', week_max)