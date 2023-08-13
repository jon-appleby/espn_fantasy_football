import requests
import pandas as pd
from setup_info import SWID, ESPN_S2, LEAGUE_ID
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import matplotlib.colors as mcolors
from adjustText import adjust_text


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


def merge_transform_data(scores_for_df, teams_for_df, draft_for_df, rank_for_df):
    """
    merge main data inputs, then create additional fields used later for plotting
    """
    # merge the first 2 datasets
    combine_df = pd.merge(scores_for_df, teams_for_df, left_on='Team1_ID', right_on='Team_ID')
    combine_df = pd.merge(combine_df, teams_for_df, left_on='Team2_ID', right_on='Team_ID')

    # drop and rename some fields
    combine_df = combine_df.drop(['Team_ID_x', 'Team_ID_y'], axis=1)
    combine_df.rename(columns={'Team_Name_x': 'team_name',
                               'Team_Name_y': 'opp_name',
                               'Team1_ID': 'team_id',
                               'Team1_Points': 'team_points',
                               'Team2_ID': 'opp_id',
                               'Team2_Points': 'opp_points',
                               'Matchup_Period': 'matchup_period'},
                      inplace=True)

    # merge in the draft and rank details
    combine_df = pd.merge(combine_df, draft_for_df, left_on='team_id', right_on='team_id')
    combine_df = pd.merge(combine_df, rank_for_df, left_on='team_id', right_on='team_id')

    # calculate league week avg, then merge into main df
    week_avg = combine_df.groupby(['matchup_period']).mean(numeric_only=True)['team_points']
    combine_df = pd.merge(combine_df, week_avg,
                          left_on='matchup_period',
                          right_on='matchup_period').rename(columns={'team_points_x': 'team_points',
                                                                     'team_points_y': 'week_avg'})

    # calculate whether each matchup is a win and/or win against avg
    combine_df['win'] = np.where(combine_df['team_points'] > combine_df['opp_points'], 1, 0)
    combine_df['all_play_win'] = np.where(combine_df['team_points'] > combine_df['week_avg'], 1, 0)

    # calculate pts over/under week avg
    combine_df['team_pts_v_avg'] = combine_df['team_points'] - combine_df['week_avg']
    combine_df['opp_pts_v_avg'] = combine_df['opp_points'] - combine_df['week_avg']

    # get diff b/w draft and final rank
    combine_df['draft_rank_diff'] = combine_df['draft_pos'] - combine_df['rank']

    # determine current average score by player
    copy_df = combine_df
    copy_df = copy_df.drop(['team_name', 'opp_name'], axis=1)
    copy_df = copy_df.expanding(min_periods=1).mean()
    # print(copy_df.to_string())

    # determine power ranking by player for each week
    # ((avg score * 6) + ((highest score ytd + lowest score ytd) x 2) + ((win % x 200) x2)) / 10

    return combine_df


def chart_draft_pos_rank(data, week, path=None):
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


def chart_draft_vs_final(data, week, path=None):
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


def chart_week_avg(data, week, path=None):
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


def chart_all_play(data, week, path=None):
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


def chart_team_median(data, week, path=None):
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


def chart_team_opp_density(data, week, path=None):
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


def curr_matchup_chart(data, curr_week, path=None):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] == curr_week]
    print(data.to_string())

    x_pt = data['team_pts_v_avg']
    y_pt = data['opp_pts_v_avg']
    label = data['team_name']

    sns.scatterplot(data=data, x=x_pt, y=y_pt,
                    hue='win', hue_order=[1, 0],
                    style='win', style_order=[1, 0],
                    palette={1: '#32a852', 0: '#a32123'})

    # fix legend labels
    plt.legend(labels=['loss', 'win'])

    # add title
    plt.title(f'Matchup Matrix - Week {curr_week}', fontsize=10)

    # update axis labels
    plt.xlabel('Team Score', size=9, color='#737373')
    plt.ylabel('Opponent Score', size=9, color='#737373')
    plt.xticks(size=9, color='#737373')
    plt.yticks(size=9, color='#737373')

    # set axis limits
    plt.xlim(-max(x_pt)-5, max(x_pt)+5)
    plt.ylim(-max(y_pt)-5, max(y_pt)+5)

    # add quadrant lines
    plt.axhline(y=0, color='#737373')
    plt.axvline(x=0, color='#737373')

    # add text to quadrants
    quad_label_dict = {'fontsize': 8,
                       'ha': 'center',
                       'va': 'center',
                       'color': '#737373'}
    plt.text(x=-13, y=-13, s='Lucky Win /\nMissed Opportunity', fontdict=quad_label_dict)
    plt.text(x=13, y=13, s='Unlucky Loss /\nTough Win', fontdict=quad_label_dict)

    # add team name as labels to each point
    text = [plt.text(x, y, f'{name}', fontdict={'size': 9, 'color': '#4d5478'})
            for (x, y, name) in zip(x_pt, y_pt, label)]
    adjust_text(text, arrowprops={'arrowstyle': '-', 'color': '#9badc9', 'lw': 0.5})

    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def print_and_save_charts(max_week=14, week_current=1):
    chart_draft_pos_rank(df, max_week, './outputs/1pos to rank.png')
    chart_draft_vs_final(df, max_week, './outputs/2diff draft to final.png')
    chart_week_avg(df, max_week, './outputs/3weekly_avg_scores.png')
    chart_all_play(df, max_week, './outputs/4wins_against_week_avg.png')
    chart_team_median(df, max_week, './outputs/5median_scores.png')
    chart_team_opp_density(df, max_week, './outputs/6score_against_opp_density.png')
    curr_matchup_chart(df, week_current, f'./outputs/week{current_week}_matchup_chart.png')


# TODO: get player ytd average score
# TODO: get player ytd power ranking

if __name__ == '__main__':
    year = 2022
    league_id = LEAGUE_ID
    boxscore_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                   f'leagues/{league_id}?view=mBoxscore'
    # use to get "rankCalculatedFinal"
    scoreboard_settings_url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
                              f'leagues/{league_id}?view=mMatchup&view=mScoreboard&view=mSettings'

    # get data and create df
    schedule_data, teams = fetch_boxscore_data(boxscore_url)
    draft_pos, rank_df = get_draftpos_rank(scoreboard_settings_url)
    score_df = create_matchup_data(schedule_data)
    team_df = create_team_data(teams)
    df = merge_transform_data(score_df, team_df, draft_pos, rank_df)

    ##################
    # run the charts #
    ##################
    # set a max week (e.g. use 14 to only see regular season)
    week_max = 14
    # set current week to use on charts that are specific to a single week
    current_week = 2
    # print_and_save_charts(week_max, current_week)

    ######################
    # prints for testing #
    ######################
    # df.to_excel('/outputs/score_data.xlsx')
    # print(df.head().to_string())
    curr_matchup_chart(df, 13)  # f'./outputs/week{current_week}_matchup_chart.png'
    # print(df.info())
    # print(df.corr(numeric_only=True).to_string())
