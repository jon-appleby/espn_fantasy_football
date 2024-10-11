import pandas as pd
from time import sleep
from weekly_scripts.act_opt_metrics import get_slates
from main.espn_api import fetch_api_data
from main.team_mapping import team_id_name


def get_injured_players(year) -> pd.DataFrame:
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
            sleep(15)
            w += 1

    full_df = pd.concat(df_list)
    full_df['player_status'] = ''
    full_df['player_status'] = full_df['player_status'].astype(object)
    full_df.loc[full_df['game status'].notnull(), 'player_status'] = 'out'
    full_df['player_status'].replace('', 'in', inplace=True)

    df = full_df.loc[full_df['position'].isin(['QB', 'WR', 'RB', 'TE'])]

    df.to_excel('../Outputs/player_injuries.xlsx', index=False)

    return df


def weekly_players(max_week_num, year, team_mapping) -> pd.DataFrame:
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
            starting_players = slate.loc[~slate['Slot'].isin(['D/ST', 'K'])]
            starting_players = starting_players[['Name', 'Slot', 'week', 'team_id', 'team_name']]
            slate_list.append(starting_players)
            # print(slate)

        print(f'week {w} complete')
        w += 1
        sleep(15)

    df = pd.concat(slate_list)

    # df.to_excel('../test/weekly_players.xlsx', index=False)

    return df


def team_injuries(injuries, fantasy_data) -> pd.DataFrame:
    """
    takes all injured players and merges with the fantasy lineup for each team

    :return: dataframe of all players on the team's roster with their injury status from NFL.com
    """

    print('\n merging injury and fantasy team data')

    df = pd.merge(left=fantasy_data, right=injuries, how='left', left_on=['Name', 'week'], right_on=['player', 'week'])
    df.columns = df.columns.str.lower()
    df['player_status'].fillna('in', inplace=True)

    df.drop(columns=['player', 'injuries', 'position', 'practice status'], inplace=True)
    df['player_status'] = df.apply(lambda row: 'out' if row['slot'] == 'IR' else row['player_status'], axis=1)
    df.rename(columns={'game status': 'game_status'}, inplace=True)

    df.to_excel('../Outputs/team_injuries.xlsx', index=False)

    return df


if __name__ == '__main__':
    season = 2024
    max_week = 6  # replace with current week, or set to 14 for full season

    teams = team_id_name(season)

    # injury status from NFL.com
    # injured_players = pd.read_excel('../Outputs/player_injuries.xlsx')
    injured_players = get_injured_players(year=season)

    # players from each fantasy team
    # weekly_players = pd.read_excel('../test/weekly_players.xlsx')
    weekly_players = weekly_players(max_week_num=max_week, year=season, team_mapping=teams)

    # combined fantasy team and injury status from NFL.com
    team_injuries = team_injuries(injuries=injured_players, fantasy_data=weekly_players)
