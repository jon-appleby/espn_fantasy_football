from main.espn_api import fetch_api_data
import json
from time import sleep

"""
Purpose: get player rankings (ROS if possible)
Attempting to use ESPN API if possible, otherwise try scraping fantasypros
https://www.fantasypros.com/nfl/rankings/ros-ppr-overall.php
https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leagues/REDACTED_LEAGUE_ID?view=mMatchup&view=mMatchupScore&scoringPeriodId=5&matchupPeriodId=5
"""

# data = fetch_api_data(views=['mMatchup', 'mMatchupScore'], year=2025,
#                       params={'scoringPeriodId': 5, 'matchupPeriodId': 5})

# use this to get players by week??
# then use kona_player_info to get ros rank maybe (how to get more than 50 players?
# for team in data['teams']:
#     if team['id'] == 6:  # remove after testing
#         roster = team['roster']['entries']
#         for player in roster:
#             print(player)
#             player_id = player['playerId']
#             player_name = player['playerPoolEntry']['player']['fullName']
#             print(f'{player_id} - {player_name}')

# for _ in range(5):
#     offset = 0
#     data = fetch_api_data(views=['kona_player_info'], year=2025,
#                           header={'X-Fantasy-Filter': json.dumps({"players": {"limit": int(2), "offset": int(50),
#                                                                               "sortDraftRanks": {"sortPriority": '100',
#                                                                                                  "sortAsc": 'true',
#                                                                                                  "value": "PPR"}}})}
#                           )
#     offset += 50
#     players = data['players']
#     for player in players:
#         player_info = {
#             'name': player['player']['fullName'],
#             'pos_rank': player['ratings']['0']['positionalRanking'],
#             'tot_rank': player['ratings']['0']['totalRanking']
#         }
#         player_data[player['id']] = player_info
#     sleep(1)

# for _ in range(5):
#     offset = 0
#     data = fetch_api_data(views=['kona_playercard'], year=2025,
#                           header={'X-Fantasy-Filter': json.dumps({"players": {"limit": int(5), "offset": int(0),
#                                                                               "sortDraftRanks": {"sortPriority": '100',
#                                                                                                  "sortAsc": 'true',
#                                                                                                  "value": "PPR"}}})}
#                           )
#     offset += 50
#     players = data['players']
#     for player in players:
#         player_info = {
#             'name': player['player']['fullName'],
#             'ppr_draft_rank': player['player']['draftRanksByRankType']['PPR']['rank'],
#             'pos_rank': player['ratings']['0']['positionalRanking'],
#             'tot_rank': player['ratings']['0']['totalRanking']
#         }
#         player_data[player['id']] = player_info
#     sleep(1)
#
# print(player_data)

player_data = {}
offset = 0

# get top 500 players
for _ in range(10):
    filters = {"players": {
        # Filters to only include players eligible at certain roster slots
        # These numbers map to ESPN slot IDs (QB = 0, RB = 2, WR = 4, TE = 6, FLEX = 23, etc.)
        "filterSlotIds": {"value": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 23, 24]},
        # Pulls stats for the 2024 season and the 2025 season
        # Requests both actual stats (0) and projected stats (1)
        "filterStatsForExternalIds": {"value": [2024, 2025]}, "filterStatsForSourceIds": {"value": [0, 1]},
        # Sorts players by projected 2025 points (appliedTotal under stats.id = 102025)
        "sortAppliedStatTotal": {"sortAsc": 'false', "sortPriority": 3, "value": "102025"},
        # Also sorts by draft ranks in PPR scoring
        "sortDraftRanks": {"sortPriority": 2, "sortAsc": 'true', "value": "PPR"},
        # Orders by percent-owned in ESPN leagues as a tertiary tiebreaker
        "sortPercOwned": {"sortAsc": 'false', "sortPriority": 4},
        # limit / offset
        "limit": 50, "offset": offset,
        # Likely “preseason/draft” ranks for 2025
        # Scoring period 5 is ESPN’s preseason period
        "filterRanksForScoringPeriodIds": {"value": [5]},
        # Only return rankings for PPR scoring format
        "filterRanksForRankTypes": {"value": ["PPR"]},
        # Rankings for eligible fantasy slots (QB, RB, WR, TE, FLEX, etc.)
        "filterRanksForSlotIds": {"value": [0, 2, 4, 6, 17, 16, 8, 9, 10, 12, 13, 24, 11, 14, 15]},
        # Value 2 means “season-long totals”
        # The additionalValue entries specify which stat sets to include:
        #     "002024" = 2024 actuals
        #     "002025" = placeholder for 2025 actuals
        #     "102025" = 2025 projections
        #     "1120255" and "022025" look like alternate splits (weekly, rest-of-season, etc.).
        "filterStatsForTopScoringPeriodIds": {"value": 2,
                                              "additionalValue": ["002025", "102025", "002024", "1120255", "022025"]}
        }
    }
    data = fetch_api_data(views=['kona_player_info'], year=2025,
                          header={'X-Fantasy-Filter': json.dumps(filters)}
                          )

    players = data['players']
    for player in players:
        if player["onTeamId"] == 0:  # not on a team
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
            '2025_projection': proj_stats['appliedTotal'],
            '2025_actual': act_stats['appliedTotal'],
            'position_rank': player['ratings']['0']['positionalRanking'],
            'total_rank': player['ratings']['0']['totalRanking'],
            'team': player['onTeamId']
        }
        player_data[player['id']] = player_info

    offset += 50
    sleep(1)

print(player_data)

