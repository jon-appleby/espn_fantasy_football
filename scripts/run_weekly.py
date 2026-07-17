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


def main(season, week):
    team_df = member_info_df(season)
    team_df = team_df[['id', 'user_name']].rename(columns={'user_name': 'team_name'})

    # -------------
    # MAIN METRICS
    # -------------
    schedule_data, _teams = fetch_boxscore_data(season)
    draft_pos, rank_df = get_draftpos_rank(season)
    score_df = create_matchup_data(schedule_data)

    weekly_team_df = team_df.rename(columns={'id': 'Team_ID', 'team_name': 'Team_Name'})
    weekly_team_df['Team_ID'] = weekly_team_df['Team_ID'].astype(str)

    full_data = merge_transform_data(score_df, weekly_team_df, draft_pos, rank_df)
    full_data.to_excel('../outputs/weekly/weekly_score_data.xlsx', index=False)

    matchup_team_order = get_matchup_team_order(full_data, week)

    # -----------------
    # ACTUAL v OPTIMAL
    # -----------------
    slate_data = create_team_slates(
        fetch_api_data(
            views=['mMatchup', 'mMatchupScore'],
            year=season,
            params={'scoringPeriodId': week, 'matchupPeriodId': week},
        ),
        week_num=week,
    )

    point_data = calculate_lineup_points(slate_data, POSITIONS, STRUCTURE)
    lineup_efficiency = create_lineup_efficiency(point_data, team_df)

    chart_actual_vs_optimal(
        lineup_efficiency,
        curr_season=season,
        curr_week=week,
        team_order=matchup_team_order,
    )

    # ----------------
    # SCORE ABOVE AVG
    # ----------------
    d = create_opp_difficulty_data(season)
    d.to_csv(f'../outputs/weekly/opponent_difficulty_{season}.csv')
    summarize_opponent_difficulty(d, season, week)
    chart_opp_difficulty(d, season, week)

    print_and_save_charts(
        data=full_data,
        curr_season=season,
        max_week=week,
        week_current=week)


if __name__ == '__main__':
    s = int(input('Season: '))
    w = int(input('Week: '))
    main(s, w)
