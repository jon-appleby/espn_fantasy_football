from main.espn_api import fetch_api_data
from main.setup_info import SWID, ESPN_S2, LEAGUE_ID
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def get_slates(data, week_num) -> dict[str: pd.DataFrame]:
    """
    Constructs week team slates with slotted position,
    position, and points (actual and ESPN projected),
    given full matchup info (`get_matchups`)

    :return dict containing team id: dataframe with slot (position, bench, or ir)
    """

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
    slates = {}

    for team in data['teams']:
        slate = []
        for p in team['roster']['entries']:
            # get name
            name = p['playerPoolEntry']['player']['fullName']

            # get actual lineup slot
            slotid = p['lineupSlotId']
            slot = slotcodes[slotid]

            # get projected and actual scores
            act, proj = 0, 0
            for stat in p['playerPoolEntry']['player']['stats']:
                if stat['scoringPeriodId'] != week_num:
                    continue
                if stat['statSourceId'] == 0:
                    act = stat['appliedTotal']
                elif stat['statSourceId'] == 1:
                    proj = stat['appliedTotal']
                else:
                    print('Error')

            # get type of player
            pos = 'Unk'
            ess = p['playerPoolEntry']['player']['eligibleSlots']
            if 0 in ess:
                pos = 'QB'
            elif 2 in ess:
                pos = 'RB'
            elif 4 in ess:
                pos = 'WR'
            elif 6 in ess:
                pos = 'TE'
            elif 16 in ess:
                pos = 'D/ST'
            elif 17 in ess:
                pos = 'K'

            slate.append([name, slotid, slot, pos, act, proj])
        slate = pd.DataFrame(slate, columns=['Name', 'SlotID', 'Slot', 'Pos', 'Actual', 'Proj'])
        slates[team['id']] = slate
    return slates


def compute_pts(slates, posns, struc):
    '''
    Given slates (`get_slates`), compute total roster pts:
    actual, optimal, and using ESPN projections

    Parameters
    --------------
    slates : `dict` of `DataFrames`
        (from `get_slates`)
    posns : `list`
        roster positions, e.g. ['QB','RB', 'WR', 'TE']
    struc : `list`
        slots per position, e.g. [1,2,2,1]

    * This is not flexible enough to handle "weird" leagues
    like 6 Flex slots with constraints on # total RB/WR

    Returns
    --------------
    `dict` of `dict`s with actual, ESPN, optimal points
    '''

    data = {}
    for tmid, slate in slates.items():
        pts = {'opts': 0, 'epts': 0, 'apts': 0}

        # ACTUAL STARTERS
        pts['apts'] = slate.query('Slot not in ["Bench", "IR"]').filter(['Actual']).sum().values[0]

        # OPTIMAL and ESPNPROJ STARTERS
        for method, cat in [('Actual', 'opts'), ('Proj', 'epts')]:
            actflex = -100  # actual pts scored by flex
            proflex = -100  # "proj" pts scored by flex
            for pos, num in zip(posns, struc):
                # actual points, sorted by either actual or proj outcome
                t = slate.query('Pos == @pos') \
                        .sort_values(by=method, ascending=False) \
                        .filter(['Actual']).values[:, 0]

                # projected points, sorted by either actual or proj outcome
                t2 = slate.query('Pos == @pos') \
                         .sort_values(by=method, ascending=False) \
                         .filter(['Proj']).values[:, 0]

                # sum up points
                pts[cat] += t[:num].sum()

                # set the next best as flex
                if pos in ['RB', 'WR', 'TE'] and len(t) > num:
                    fn = t[num] if method == 'Actual' else t2[num]
                    if fn > proflex:
                        actflex = t[num]
                        proflex = fn

            pts[cat] += actflex

        data[tmid] = pts

    return data


def get_team_info(year, league):
    '''
    get team name info and concat
    '''

    data = fetch_api_data(views=['mTeam'], year=year, league=league)

    team_df_temp = [[
        team_info['id'],
        team_info['name']]
        for team_info in data['teams']]
    teams = pd.DataFrame(team_df_temp, columns=['id', 'team_name'])

    return teams


def transform_data(data, team):
    """
    get data and teams, merge and prepare data for use later
    """
    point_df = pd.DataFrame(data).transpose()
    point_df['TeamID'] = range(1, 1 + len(point_df))
    point_df = pd.merge(point_df, team[['id', 'team_name']], left_on='TeamID', right_on='id', how='left')
    point_df = point_df.rename(columns={'opts': 'optimal_pts',
                                        'apts': 'actual_pts',
                                        'epts': 'espn_proj',
                                        'TeamID': 'team_id'}).drop(columns='id')
    point_df['missed_pts'] = round(point_df['optimal_pts'] - point_df['actual_pts'], 2)
    point_df['efficiency'] = (round(point_df['actual_pts'] / point_df['optimal_pts'], 3) * 100)

    return point_df


def chart_oae_pts(data_input, curr_week=1):
    sns.set_theme(style='darkgrid')

    # sort for chart
    data = data_input.sort_values(by='actual_pts', ascending=False)

    actual_pt_color = 'teal'
    optimal_pt_color = 'gray'
    espn_proj_color = 'purple'
    # Set up the figure and axes
    plt.figure(figsize=(10, 8))
    ax = sns.stripplot(data=data, x='actual_pts', y='team_name', marker='o', size=10, color=actual_pt_color)

    # Add line starting at a_pts and end at o_pts
    ax.hlines(y=data['team_name'], xmin=data['actual_pts'], xmax=data['optimal_pts'],
              color=optimal_pt_color, linewidth=4, linestyles='-')

    # Add dots at the end of the lines (optimal_pts and actual_pts)
    plt.scatter(data['optimal_pts'], range(len(data)), color=optimal_pt_color, marker='|', s=120, label='optimal_pts')
    plt.scatter(data['actual_pts'], range(len(data)), color=actual_pt_color, marker='o', s=120, label='actual_pts')
    plt.scatter(data['espn_proj'], range(len(data)), color=espn_proj_color, marker='|', s=60, label='espn_proj')

    # Annotate actual_pts on the left and optimal_pts on the right
    for index, row in data.iterrows():
        ax.annotate(f'{row["actual_pts"]:.2f}',  # :.2f formats the value of the float to 2 decimals
                    xy=(row['actual_pts'], row['team_name']),  # specify where to plot the text
                    xytext=(-9, -1),  # specify offset of the xy coords above
                    textcoords='offset points', color=actual_pt_color,
                    fontsize=8, ha='right', va='center')

        ax.annotate(f'{row["optimal_pts"]:.2f}', xy=(row['optimal_pts'], row['team_name']),
                    xytext=(5, -1),
                    textcoords='offset points', color=optimal_pt_color,
                    fontsize=8, ha='left', va='center')

    # Set axis labels and title
    plt.xlim(min(data['actual_pts'] - 10), max(data['optimal_pts'] + 10))
    plt.xlabel('Points', size=9)
    plt.ylabel('Team', size=9)
    plt.xticks(size=9, color='#737373')
    plt.yticks(size=9, color='#737373')
    plt.title(f'Actual vs Optimal Points - Week {curr_week}', size=10)

    # add point labels
    # text = [plt.text(x, y, f'{name}', fontdict={'size': 9, 'color': '#4d5478'})
    #         for (x, y, name) in zip(x_pt, y_pt, label)]

    # Add legend
    plt.legend()

    plt.savefig(f'../outputs/10-week{curr_week}_actual_vs_optimal.png', bbox_inches='tight')

    plt.show()


if __name__ == '__main__':
    swid = SWID
    espn = ESPN_S2
    league_id = LEAGUE_ID
    positions = ['QB', 'RB', 'WR', 'Flex', 'TE', 'D/ST', 'K']
    structure = [1, 2, 2, 1, 1, 1, 1]

    season = 2025
    week = 17

    # https://fantasy.espn.com/apis/v3/games/ffl/seasons/2023/segments/0/leagues/REDACTED_LEAGUE_ID?view=mMatchup&view=mMatchupScore&scoringPeriodId=9&matchupPeriodId=9
    slate_data = get_slates(
        fetch_api_data(views=['mMatchup', 'mMatchupScore'], year=season,
                       params={'scoringPeriodId': week, 'matchupPeriodId': week}),
        week_num=week
    )
    point_data = compute_pts(slate_data, positions, structure)
    team_df = get_team_info(season, league_id)

    # prints for testing
    # print_output = transform_data(point_data, team_df)
    # print(print_output.to_string())

    chart_oae_pts(transform_data(point_data, team_df), week)
