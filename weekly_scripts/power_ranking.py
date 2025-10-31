from time import sleep
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from main.espn_api import fetch_api_data


def get_player_data(year: int, week: int) -> dict:
    prev_year = year - 1
    player_data = {}
    offset = 0

    filt_week = week + 1

    # get top 500 players
    for _ in range(10):
        # filters from api call on espn website players > projections > 2025 projections
        filters = {'players': {
            # Filters to only include players eligible at certain roster slots
            # These numbers map to ESPN slot IDs (QB = 0, RB = 2, WR = 4, TE = 6, FLEX = 23, etc.)
            'filterSlotIds': {'value': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23, 24]},
            # Pulls stats for the 2024 season and the 2025 season
            # Requests both actual stats (0) and projected stats (1)
            'filterStatsForExternalIds': {'value': [prev_year, year]}, 'filterStatsForSourceIds': {'value': [0, 1]},
            # Sorts players by projected 2025 points (appliedTotal under stats.id = 102025)
            'sortAppliedStatTotal': {'sortAsc': 'false', 'sortPriority': 3, 'value': '102025'},
            # Also sorts by draft ranks in PPR scoring
            'sortDraftRanks': {'sortPriority': 2, 'sortAsc': 'true', 'value': 'PPR'},
            # Orders by percent-owned in ESPN leagues as a tertiary tiebreaker
            'sortPercOwned': {'sortAsc': 'false', 'sortPriority': 4},
            # limit / offset
            'limit': 50, 'offset': offset,
            # Likely “preseason/draft” ranks for 2025
            # Scoring period 5 is ESPN’s preseason period
            'filterRanksForScoringPeriodIds': {'value': [filt_week]},
            # Only return rankings for PPR scoring format
            'filterRanksForRankTypes': {'value': ['PPR']},
            # Rankings for eligible fantasy slots (QB, RB, WR, TE, FLEX, etc.)
            'filterRanksForSlotIds': {'value': [0, 2, 4, 6, 17, 16, 8, 9, 10, 12, 13, 24, 11, 14, 15]},
            # Value 2 means “season-long totals”
            # The additionalValue entries specify which stat sets to include:
            #     '002024' = 2024 actuals
            #     '002025' = placeholder for 2025 actuals
            #     '102025' = 2025 projections
            #     '1120255' and '022025' look like alternate splits (weekly, rest-of-season, etc.).
            'filterStatsForTopScoringPeriodIds': {'value': 2,
                                                  'additionalValue': ['002025', '102025', '002024',
                                                                      f'112025{filt_week}', '022025']}
        }
        }

        # get espn player data
        data = fetch_api_data(views=['kona_player_info'], year=year,
                              header={'X-Fantasy-Filter': json.dumps(filters)}
                              )

        players = data['players']
        for player in players:
            if player['onTeamId'] == 0:  # not on a team
                continue
            stats = player['player']['stats']
            proj_stats = next(
                (s for s in stats if s['id'] == '102025')
            )
            act_stats = next(
                (s for s in stats if s['id'] == '002025')
            )
            player_info = {
                'name': player['player']['fullName'],
                'projection': proj_stats['appliedTotal'],
                'actual': act_stats['appliedTotal'],
                'position_rank': player['ratings']['0']['positionalRanking'],
                'total_rank': player['ratings']['0']['totalRanking'],
                'team': player['onTeamId']
            }
            player_data[player['id']] = player_info

        offset += 50
        sleep(1)

    return player_data


def summarize_teams(data, year, week) -> pd.DataFrame:
    df = pd.DataFrame(data)
    # df = pd.read_json(data)  # use when reading from saved / test data
    df = df.T

    # calculate FY projection based on actual YTD pts
    df['actual_projection'] = (df['actual'] / week) * 14

    df['owner'] = df['team'].map({1: 'Jared',
                                  2: 'Lucas',
                                  3: 'Prem',
                                  4: 'Cole',
                                  5: 'Palak',
                                  6: 'Jon',
                                  7: 'Austin',
                                  8: 'Chris',
                                  9: 'Casey',
                                  10: 'Mitch B',
                                  11: 'Mitch P',
                                  12: 'Matt'})

    # fix players who are unranked (e.g. injured)
    df['position_rank'] = df['position_rank'].replace(0, 9999)
    df['total_rank'] = df['total_rank'].replace(0, 9999)

    # determine overall value for each player
    df['position_value'] = 1 / df['position_rank']
    df['total_value'] = 1 / df['total_rank']
    df['adj_value'] = (
            0.8 * df['projection'] * df['position_value'] +
            0.2 * df['projection'] * df['total_value']
    )

    print(df.to_string())

    # aggregate FY projection, YTD-based projections, and player value
    df = df.groupby('owner').agg({
        'projection': 'sum',
        'actual_projection': 'sum',
        'adj_value': 'sum'
    }).reset_index()

    # calculate power ranking w/ weighted rankings
    df['power_rank'] = (
            0.2 * df['projection'] +  # overall projection matters some
            0.6 * df['actual_projection'] +  # using real data means more
            0.2 * df['adj_value']  # adjusted player values
    )

    df = df.sort_values(by='power_rank', ascending=False)

    df['week'] = week
    df['year'] = year

    print(df.to_string())
    return df


def create_chart(data: pd.DataFrame) -> None:
    # add column for max(projection, actual_projection)
    data['max_proj'] = data[['projection', 'actual_projection']].max(axis=1)

    # sort teams by power_rank (highest on top)
    data = data.sort_values('power_rank', ascending=True)

    fig, ax = plt.subplots(figsize=(6, 4))

    # horizontal bars for power rank
    ax.barh(
        data['owner'], data['power_rank'],
        color='#6e6e6e', alpha=0.8
    )

    # dot for max projection
    ax.scatter(
        data['max_proj'], data['owner'],
        color='#1f1f1f', s=25, zorder=2
    )

    ax.set_xlabel('Power Rank Score', fontsize=8)
    ax.set_ylabel('Team', fontsize=8)
    ax.set_title('Team Power Rankings', fontsize=10)

    ax.tick_params(axis='both', labelsize=8)

    plt.tight_layout()
    plt.show()


def save_data(data: pd.DataFrame, week: int, year: int) -> None:
    file = pd.read_excel('../Outputs/power_ranking.xlsx')

    merged = pd.merge(left=data, right=file[['owner', 'week', 'year']],
                      on=['owner', 'week', 'year'], how='left', indicator=True)

    # get only the records that don't exist on the file already
    new_records = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])

    df = pd.concat([file, new_records]).sort_values(['week', 'year', 'power_rank'], ascending=False)

    df.to_excel('../Outputs/power_ranking.xlsx', sheet_name='Sheet1', index=False)


if __name__ == '__main__':
    y = 2025
    w = 8
    d = get_player_data(y, w)

    # with open('../test/test_player_info.json', 'w') as f:
    #     json.dump(d, f)
    # d = '../test/test_player_info.json'

    t = summarize_teams(d, y, w)
    save_data(t, w, y)

    # create_chart(t)

    """
    - based on the eyeball test it seems to be relatively accurate
    - this takes the full-year projections for each player, player points YTD, overall player value, etc. and 
    scales forward to estimate full-season rankings for each team
    - the bar is your power rank score, the dot is the highest score between FY player projection, forecasted
    projections, etc. (this could be based on projections for injured players, etc.)
    """
