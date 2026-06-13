import os

from dotenv import load_dotenv

from espn.constants import POSITIONS, STRUCTURE
from espn.espn_client import fetch_api_data
from espn.team_mapping import member_info_df
from metrics.weekly.actual_vs_optimal import (
    calculate_lineup_points,
    chart_actual_vs_optimal,
    create_lineup_efficiency,
    create_team_slates,
    get_matchup_team_order,
)
from metrics.weekly.opponent_difficulty import (
    chart_opp_difficulty,
    create_opp_difficulty_data,
    summarize_opponent_difficulty,
)
from metrics.weekly.weekly_metrics import (
    create_matchup_data,
    fetch_boxscore_data,
    get_draftpos_rank,
    merge_transform_data,
    print_and_save_charts,
)

load_dotenv()
LEAGUE_ID = os.getenv('LEAGUE_ID')

SEASON = 2025
WEEK = 17


def main():
    team_df = member_info_df(SEASON)
    team_df = team_df[['id', 'user_name']].rename(columns={'user_name': 'team_name'})

    # -------------
    # MAIN METRICS
    # -------------
    schedule_data, _teams = fetch_boxscore_data(SEASON)
    draft_pos, rank_df = get_draftpos_rank(SEASON)
    score_df = create_matchup_data(schedule_data)

    weekly_team_df = team_df.rename(columns={'id': 'Team_ID', 'team_name': 'Team_Name'})
    weekly_team_df['Team_ID'] = weekly_team_df['Team_ID'].astype(str)

    full_data = merge_transform_data(score_df, weekly_team_df, draft_pos, rank_df)
    full_data.to_excel('../outputs/weekly_score_data.xlsx', index=False)

    matchup_team_order = get_matchup_team_order(full_data, WEEK)

    # -----------------
    # ACTUAL v OPTIMAL
    # -----------------
    slate_data = create_team_slates(
        fetch_api_data(
            views=['mMatchup', 'mMatchupScore'],
            year=SEASON,
            params={'scoringPeriodId': WEEK, 'matchupPeriodId': WEEK},
        ),
        week_num=WEEK,
    )

    point_data = calculate_lineup_points(slate_data, POSITIONS, STRUCTURE)
    lineup_efficiency = create_lineup_efficiency(point_data, team_df)

    chart_actual_vs_optimal(
        lineup_efficiency,
        curr_week=WEEK,
        team_order=matchup_team_order,
    )

    # ----------------
    # SCORE ABOVE AVG
    # ----------------
    d = create_opp_difficulty_data(SEASON)
    d.to_csv(f'../outputs/opponent_difficulty_{SEASON}.csv')
    summarize_opponent_difficulty(d, SEASON)
    chart_opp_difficulty(d, SEASON)

    print_and_save_charts(full_data, WEEK, WEEK)


if __name__ == '__main__':
    main()
