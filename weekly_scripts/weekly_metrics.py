from main.espn_api import fetch_api_data
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as plticker
import seaborn as sns
import numpy as np
from adjustText import adjust_text


def fetch_boxscore_data(curr_year):
    data = fetch_api_data(views=['mBoxscore'], year=curr_year)
    return data['schedule'], data['teams']


def get_draftpos_rank(curr_year):
    data = fetch_api_data(views=['mMatchup', 'mScoreboard', 'mSettings'], year=curr_year)

    # iterate through the list and append to dict using index + 1 as team ID
    order = data['settings']['draftSettings']['pickOrder']
    pick_order = []
    for index, pos in enumerate(order):
        index += 1
        pick_order.append({'team_id': str(pos), 'draft_pos': index})

    rank_data = fetch_api_data(views=['mTeam'], year=curr_year)
    # iterate through list of teams and get rank + team id
    rank_list = []
    team_list = rank_data['teams']
    for team in team_list:
        rank = team['currentProjectedRank']
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
    # renamed from all_play_win
    combine_df['win_vs_avg'] = np.where(combine_df['team_points'] > combine_df['week_avg'], 1, 0)

    # calculate pts over/under week avg
    combine_df['team_pts_v_avg'] = combine_df['team_points'] - combine_df['week_avg']
    combine_df['opp_pts_v_avg'] = combine_df['opp_points'] - combine_df['week_avg']

    # get diff b/w draft and final rank
    combine_df['draft_rank_diff'] = combine_df['draft_pos'] - combine_df['rank']

    # determine current average score by player
    team_avg = combine_df.groupby(by='team_id')['team_points'].mean().reset_index()
    combine_df = pd.merge(combine_df, team_avg, left_on='team_id', right_on='team_id') \
        .rename(columns={'team_points_x': 'team_points', 'team_points_y': 'team_avg_full'})

    # get highest/lowest points and win % for each team
    high_points = combine_df.groupby(by='team_id')['team_points'].max().reset_index().rename(
        columns={'team_points': 'team_hi_pts_full'})
    low_points = combine_df.groupby(by='team_id')['team_points'].min().reset_index().rename(
        columns={'team_points': 'team_lo_pts_full'})
    win_pct = combine_df.groupby(by='team_id')['win'].mean().reset_index().rename(
        columns={'win': 'win_pct_full'})
    combine_df = combine_df.merge(high_points, on='team_id') \
        .merge(low_points, on='team_id') \
        .merge(win_pct, on='team_id')

    # determine power ranking by player for each week
    #   ((avg score * 6) + ((highest score ytd + lowest score ytd) x 2) + ((win % x 200) x2) / 10
    combine_df['power_rank_full'] = (
                                            (
                                                    (combine_df['team_avg_full'] * 6) + combine_df['team_hi_pts_full']
                                            ) +
                                            (
                                                    (combine_df['win_pct_full'] * 200) * 2
                                            )
                                    ) / 10

    ####################
    # create ytd stats #
    ####################
    # sort dataframe to ensure we add up from the matchup periods before
    combine_df = combine_df.sort_values(by='matchup_period')

    # group the data by 'team_id' then calculate avg, hi, lo, and win pct
    combine_df['team_avg_ytd'] = combine_df.groupby('team_id')['team_points'].cumsum() \
                                 / combine_df.groupby('team_id').cumcount().add(1)
    combine_df['team_hi_pts_ytd'] = combine_df.groupby('team_id')['team_points'].cummax()
    combine_df['team_lo_pts_ytd'] = combine_df.groupby('team_id')['team_points'].cummin()
    combine_df['win_pct_ytd'] = combine_df.groupby('team_id')['win'].cumsum() \
                                / combine_df.groupby('team_id').cumcount().add(1)

    # create power rankings by week
    combine_df['power_rank_ytd'] = (
                                           (
                                                   (combine_df['team_avg_ytd'] * 6) + combine_df['team_hi_pts_ytd']
                                           ) +
                                           (
                                                   (combine_df['win_pct_ytd'] * 200) * 2
                                           )
                                   ) / 10

    combine_df['power_rank_ytd_asrank'] = combine_df.groupby('matchup_period')['power_rank_ytd'].rank(ascending=False)

    # create all_play_win for each week, rank team points minus 1 to excluding "playing self"
    combine_df['all_play_win'] = combine_df.groupby('matchup_period')['team_points'].rank() - 1

    combine_df = combine_df.sort_values(by='matchup_period')

    return combine_df


def chart_draft_pos_rank(data, week, path=None):
    """ charts the draft position vs the current position through max_weeks """

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

    # all play win count, ratio, and actual ratio
    all_play = data.groupby(data['team_name'])['all_play_win'].sum().sort_values(ascending=False).reset_index()
    all_play['all_play_ratio'] = all_play.all_play_win / (week * 11)

    actual_ratio = data.loc[data['matchup_period'] == week][['team_name', 'win_pct_ytd']]
    all_play = pd.merge(all_play, actual_ratio, how='left', left_on='team_name', right_on='team_name')

    # calc difference
    all_play['ratio_diff'] = round(all_play.win_pct_ytd - all_play.all_play_ratio, 2)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=all_play,
                y='team_name',
                x='all_play_ratio',
                color='#1c6689',
                label='All Play Ratio',
                alpha=0.9)
    sns.barplot(data=all_play,
                y='team_name',
                x='win_pct_ytd',
                color='#b0b0b0',
                label='Actual Ratio',
                alpha=0.7)

    for i, team in all_play.iterrows():
        if team.ratio_diff < 0:
            text = team.ratio_diff
        else:
            text = f'+{team.ratio_diff}'
        plt.text(team.all_play_ratio + 0.01,
                 float(i),
                 text,
                 ha='left', va='center',
                 fontdict={'family': 'arial', 'size': 9, 'color': '#262626'}
                 )

    # set labels / legend
    plt.title(f'All Play Win/Loss for Weeks {min(data["matchup_period"])}-{max(data["matchup_period"])}')
    plt.ylabel('Team')
    plt.xlabel('Win/Loss Ratio')
    plt.legend(loc='lower right')

    # set x ticks
    plt.xticks([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
               ['0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%'])

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
        plt.text(box_chart_order.index(team_name),
                 label_y,
                 rank,
                 ha='center', va='bottom')
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


def chart_power_rank_by_week(data, week, path=None):
    sns.set_theme(style='darkgrid', palette=None)

    # Filter to only records in time period
    data = data.loc[data['matchup_period'] <= week]

    x_pt = data['matchup_period']
    y_pt = data['power_rank_ytd_asrank']
    label = data['team_name']

    fig, ax = plt.subplots()

    custom_palette = ['#74aecc', '#0f78bf', '#b2df8a', '#33a02c',
                      '#fb9a99', '#e31a1c', '#bd8844', '#ff7f00',
                      '#be94d4', '#6a3d9a', '#c7c775', '#b15928']

    # Plot the lineplot
    plot = sns.lineplot(data=data, x=x_pt, y=y_pt,
                        hue=label, palette=custom_palette,
                        linewidth=3,
                        markers=True, marker='o', markersize=7)

    # set labels at end of lines
    for line, name in zip(ax.lines, label.tolist()):
        if len(line.get_ydata()) == 0:
            continue

        y = line.get_ydata()[-1]
        x = line.get_xdata()[-1]

        if not np.isfinite(y):
            y = next(reversed(line.get_ydata()[~line.get_ydata().mask]), float("nan"))
        if not np.isfinite(y) or not np.isfinite(x):
            continue

        text = ax.annotate(name,
                           xy=(x, y),
                           xytext=(12, -2),
                           color=line.get_color(),
                           xycoords=(ax.get_xaxis_transform(),
                                     ax.get_yaxis_transform()),
                           textcoords="offset points",
                           fontsize=8)

        text_width = (text.get_window_extent(
            fig.canvas.get_renderer()).transformed(ax.transData.inverted()).width)
        if np.isfinite(text_width):
            ax.set_xlim(ax.get_xlim()[0], text.xy[0] + text_width * 1.05)

    # set axis labels and title
    plt.xlim(0.5, max(x_pt) + 0.5)
    plt.xlabel('Week', size=9)
    plt.ylabel('Power Rank', size=9)
    plt.xticks(size=9, color='#737373')
    plt.yticks(size=9, color='#737373')
    plt.title(f'Power Rank by Week thru {week}', size=10)
    loc = plticker.MultipleLocator(base=1.0)  # this locator puts ticks at regular intervals
    plot.xaxis.set_major_locator(loc)

    plot.invert_yaxis()

    # Remove the legend
    plot.legend().set_visible(False)

    plt.tight_layout()

    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def curr_powerrank_vs_rank(data, curr_week, path=None):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] == curr_week]

    """
    calculate power rank using weeks up until current week
    same calculation used in transform_data function, but re-calculating below after filtering on week
    this allows for seeing intra-year or historical power ranking
    """

    # sort data for chart
    data = data.sort_values(by='power_rank_ytd_asrank')

    # Create chart
    rank_color = '#3da339'  # green
    rank_marker = 'o'
    power_rank_color = '#9c9c9c'  # grey
    ax = sns.stripplot(data=data, x='team_name', y='rank', marker=rank_marker, size=10, color=rank_color)

    # Add line starting at o_pts and end at a_pts (flipped)
    ax.vlines(x=data['team_name'], ymin=data['power_rank_ytd_asrank'], ymax=data['rank'],
              color=power_rank_color, linewidth=3, linestyles='-')

    # Add dots at the end of the lines (power_rank and rank)
    plt.scatter(range(len(data)), data['power_rank_ytd_asrank'],
                color=power_rank_color, marker='_', s=120, label='Power Rank')
    plt.scatter(range(len(data)), data['rank'],
                color=rank_color, marker=rank_marker, s=120, label='Actual Rank (Final)')

    # Set labels and title
    plt.xlabel('Team', size=9)  # Adjust x-axis label
    plt.ylabel('Ranking', size=9)  # Adjust y-axis label
    plt.xticks(range(len(data)), data['team_name'], rotation=45, ha='right', size=9,
               color='#737373')  # Adjust x-axis ticks
    plt.yticks(size=9, color='#737373')
    plt.title(f'Final Rank vs Power Rank Points - Week {curr_week}', size=10)

    ax.invert_yaxis()

    plt.text(0, 12, 'Power Ranking: based on an "expected" score for each team\n'
                    'by weighting the average score, extreme high/lows, and win %\n\n'
                    'Final Ranking: the final rank of each team per ESPN', fontdict={'fontsize': 6,
                                                                                     'ha': 'left',
                                                                                     'va': 'bottom',
                                                                                     'color': 'grey'})

    plt.legend(fontsize=8)
    plt.tight_layout()
    if path:
        plt.savefig(path, bbox_inches='tight')
    plt.show()


def curr_matchup_chart(data, curr_week, path=None):
    sns.set_theme(style='darkgrid', palette=None)
    data = data.loc[data['matchup_period'] == curr_week]

    x_pt = data['team_pts_v_avg']
    y_pt = data['opp_pts_v_avg']
    label = data['team_name']
    # Replace values in the 'win' column using .loc
    data.loc[data['win'] == 1, 'win'] = 'win'
    data.loc[data['win'] == 0, 'win'] = 'loss'

    sns.scatterplot(data=data, x=x_pt, y=y_pt,
                    hue='win',
                    hue_order=['win', 'loss'],
                    style='win',
                    style_order=['win', 'loss'],
                    palette={'win': '#32a852', 'loss': '#a32123'})

    # fix legend labels
    plt.legend(title='Result')

    # add title
    plt.title(f'Matchup Matrix - Week {curr_week}', fontsize=10)

    # update axis labels
    plt.xlabel('Team Score Over/Under Average', size=9, color='#737373')
    plt.ylabel('Opponent Score Over/Under Average', size=9, color='#737373')
    plt.xticks(size=9, color='#737373')
    plt.yticks(size=9, color='#737373')

    # set axis limits
    xmin = (-max(abs(x_pt))) - 5
    xmax = (max(abs(x_pt))) + 5
    ymin = (-max(abs(y_pt))) - 5
    ymax = (max(abs(y_pt))) + 5
    plt.xlim(xmin, xmax)
    plt.ylim(ymin, ymax)

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


def print_and_save_charts(data, max_week=14, week_current=1):
    chart_draft_pos_rank(data, max_week, f'../outputs/1-pos_to_rank_max{max_week}.png')
    chart_draft_vs_final(data, max_week, f'../outputs/2-diff_draft_to_final_max{max_week}.png')
    chart_week_avg(data, max_week, f'../outputs/3-weekly_avg_scores_max{max_week}.png')
    chart_all_play(data, max_week, f'../outputs/4-all_play_wins{max_week}.png')
    chart_team_median(data, max_week, f'../outputs/5-median_scores_max{max_week}.png')
    chart_team_opp_density(data, max_week, f'../outputs/6-score_against_opp_density_max{max_week}.png')
    chart_power_rank_by_week(full_data, max_week, f'../outputs/7-power_ranking_by_week_max{max_week}.png')
    curr_powerrank_vs_rank(data, week_current, f'../outputs/8-week{week_current}_power_ranking.png')
    curr_matchup_chart(data, week_current, f'../outputs/9-week{week_current}_matchup_chart.png')


if __name__ == '__main__':
    year = 2024
    # run the charts
    week_max = 10  # set a max week (e.g. use 14 to only see regular season) **max 17**
    current_week = 10  # set current week to use on charts that are specific to a single week **max 17**

    # get data and create df
    schedule_data, teams = fetch_boxscore_data(year)
    draft_pos, rank_df = get_draftpos_rank(year)
    score_df = create_matchup_data(schedule_data)
    team_df = create_team_data(teams)
    full_data = merge_transform_data(score_df, team_df, draft_pos, rank_df)

    print_and_save_charts(full_data, week_max, current_week)

    # prints for testing
    print(full_data.head(24).sort_values(by='team_id').to_string())
    full_data.to_excel('../outputs/weekly_score_data.xlsx', index=False)
