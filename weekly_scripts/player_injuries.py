import pandas as pd
import numpy as np
from time import sleep
import matplotlib.pyplot as plt
import seaborn as sns
from adjustText import adjust_text

from weekly_scripts.act_opt_metrics import get_slates
from main.espn_api import fetch_api_data
from main.team_mapping import team_id_name


def nfl_injuries(year) -> pd.DataFrame:
    """
    pull ALL injured players for all weeks (1-14) from nfl.com

    "injured" players includes out, questionable, and doubtful. the NFL data does not appear to update
    once a player moves to out status from questionable

    filter to QB, WR, RB, TE and game status of out
    :return: dataframe
    """
    print('\ngetting injured players')
    w = 1
    max_w = 14

    df_list = []
    for _ in range(max_week):
        url = f'https://www.nfl.com/injuries/league/{year}/reg{w}'
        try:
            week_df_list = pd.read_html(url)
        except ValueError:
            print(f'weeks {w}-{max_w} not populated yet')
            break
        else:
            for d in week_df_list:
                d.columns = d.columns.str.lower()
                d['week'] = w
                df_list.append(d)
            print(f'week {w} complete')
        finally:
            sleep(5)
            w += 1

    full_df = pd.concat(df_list)
    full_df['player_status'] = ''
    full_df['player_status'] = full_df['player_status'].astype(object)

    # set status to 'out' for Q, D, or Out status, and 'in' for anybody without a status
    full_df.loc[full_df['game status'].notnull(), 'player_status'] = 'out'
    full_df['player_status'].replace('', 'in', inplace=True)

    df = full_df.loc[full_df['position'].isin(['QB', 'WR', 'RB', 'TE'])]

    df.to_excel('./Outputs/player_injuries.xlsx', index=False)

    return df


def fantasy_players(max_week_num, year, team_mapping) -> pd.DataFrame:
    """
    pull all players for each team by week, excluding K & D/ST

    :return: dataframe of player name, slot position, week, and team name
    """

    print('\ngetting weekly players for each team')

    w = 1
    slate_list = []
    for _ in range(max_week_num):
        espn_data = fetch_api_data(views=['mMatchup', 'mMatchupScore'], year=year,
                                   params={'scoringPeriodId': w, 'matchupPeriodId': w})
        slates = get_slates(espn_data, week_num=w)
        for team_id, slate in slates.items():
            slate['week'] = w
            slate['team_id'] = team_id
            slate['team_name'] = slate['team_id'].map(team_mapping)
            starting_players = slate.loc[~slate['Pos'].isin(['D/ST', 'K'])]
            # starting_players = starting_players[['Name', 'Slot', 'Pos', 'week', 'team_id', 'team_name']]
            slate_list.append(starting_players)
            # print(slate.head().to_string())

        print(f'week {w} complete')
        w += 1
        sleep(5)

    df = pd.concat(slate_list)

    return df


def team_injuries(injuries, fantasy_data) -> pd.DataFrame:
    """
    takes all injured players and merges with the fantasy lineup for each team

    :return: dataframe of all players on the team's roster with their injury status from NFL.com
    """

    print('\nmerging injury and fantasy team data')

    df = pd.merge(left=fantasy_data, right=injuries, how='left', left_on=['Name', 'week'], right_on=['player', 'week'])
    df.columns = df.columns.str.lower()

    # update status to 'out' if the player is on IR or if there was no status from NFL.com (which already
    # marks 'in' for players in the table with no status
    df['player_status'].fillna('in', inplace=True)
    df['player_status'] = df.apply(lambda row: 'out' if row['slot'] == 'IR' else row['player_status'], axis=1)
    df.rename(columns={'game status': 'game_status'}, inplace=True)

    df.drop(columns=['player', 'injuries', 'position', 'practice status'], inplace=True)

    def player_status_weight(row):
        if row['actual'] > 0 or row['player_status'] == 'in':
            return 0
        elif row['game_status'] == 'Questionable':
            return 1
        elif row['game_status'] == 'Doubtful':
            return 1
        elif row['game_status'] == 'Out' or row['slot'] == 'IR':
            return 1

    df['player_status_weight'] = df.apply(player_status_weight, axis=1)

    df.to_excel('./Outputs/team_injuries.xlsx', index=False)

    print(df.head().to_string())

    return df


def chart_injuries(data, max_week_num):
    custom_palette = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e',
                      '#9467bd', '#e377c2', '#2b8c51', '#bcbd22',
                      '#1f4b99', '#8c564b', '#17becf', '#b06b2f']
    filtered = data.groupby(by=['team_name', 'week'])['player_status_weight'].sum().reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.barplot(data=filtered,
                x='week',
                y='player_status_weight',
                hue='team_name',
                palette=custom_palette,
                ax=ax,
                legend=False
                )

    for bar, (_, row) in zip(ax.patches, filtered.iterrows()):
        x_value = bar.get_x() + bar.get_width() / 2  # X coordinate (center of the bar)
        y_value = bar.get_height()  # Y coordinate (height of the bar)

        # display player_status_weight on top of each bar
        ax.text(x=x_value+0.01, y=y_value+0.03, s=f'{y_value:.2f}', ha='center', va='bottom',
                fontsize=6, color='black', rotation='vertical')

        # display team_name within each bar
        ax.text(x=x_value+0.008, y=y_value / 2, s=row['team_name'], ha='center', va='center',
                fontsize=7, color='white', rotation='vertical')

    plt.xlabel('Week', size=9)
    plt.ylabel('Player Injuries', size=9)
    plt.xticks(size=9, color='#737373')
    plt.yticks(size=9, color='#737373')

    path = f'./Outputs/11-week_{max_week_num}_player_injuries.png'
    plt.savefig(path, bbox_inches='tight')

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    season = 2025
    max_week = 2  # replace with current week, or set to 14 for full season

    teams = team_id_name(season)

    # injury status from NFL.com
    # injured_players = pd.read_excel('./Outputs/player_injuries.xlsx')
    injured_players = nfl_injuries(year=season)

    # players from each fantasy team
    # weekly_players = pd.read_excel('../test/weekly_players.xlsx')
    weekly_players = fantasy_players(max_week_num=max_week, year=season, team_mapping=teams)

    # combined fantasy team and injury status from NFL.com
    team_injuries = team_injuries(injuries=injured_players, fantasy_data=weekly_players)

    # create chart
    chart_injuries(team_injuries, max_week)

########################################################################################################################
#
#   - This uses NFL data for injuries, because ESPN Fantasy API does not include
# historical injury status. Sometimes NFL lists players as Questionable or Doubtful
# even though they play
#   - To account for this I use a "weight" based on player status and/or slot position:
#    - If the player scored any pts that week, then 0
#    - Else if NFL status is Out or ESPN slot is IR, then 3
#    - Else if status is Doubtful, then 2
#    - Else if Questionable, then 1
#    - Else 0
#   - Does not include K and D/ST
#   - Will be skewed due to teams holding players on IR who are out for the rest of season
#
#   This should balance whether the players were actually out, but still won't be perfect
#   Also, it's not possible with the data I have so far to tell the actual impact
# of a player being out. E.g. somebody like CMC being out is worse than Gus Edwards. I was
# considering using weekly rankings for this, but most already take into account
# the player's injury status. Historical pts per game also may not be a great representation
# of expected output. If anybody has any ideas let me know
#
########################################################################################################################

# todo - player status "weight"
#   if (status Out) and proj > 10 then 6
#   elif (status Out or slot IR) then 3
#   elif status Doubtful then 2
#   elif status Questionable then 1
#   else 0
