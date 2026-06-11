import os
from dotenv import load_dotenv

from espn.espn_client import fetch_api_data
from espn.team_mapping import member_info_df
from metrics.weekly_scripts.actual_vs_optimal import calculate_lineup_points, chart_actual_vs_optimal, create_lineup_efficiency, create_team_slates
from metrics.weekly_scripts.opponent_difficulty import create_opp_difficulty_data, summarize_opponent_difficulty, chart_opp_difficulty
from metrics.weekly_scripts.weekly_metrics import fetch_boxscore_data, get_draftpos_rank, create_matchup_data, \
    merge_transform_data, print_and_save_charts
from espn.constants import STRUCTURE, POSITIONS, SLOT_CODES

load_dotenv()
LEAGUE_ID = os.getenv('LEAGUE_ID')

SEASON = 2025
WEEK = 17


def main():
    # ---------------- #
    # ACTUAL v OPTIMAL #
    # ---------------- #
    slate_data = create_team_slates(
        fetch_api_data(views=['mMatchup', 'mMatchupScore'],
                       year=SEASON,
                       params={'scoringPeriodId': WEEK, 'matchupPeriodId': WEEK}),
                       week_num=WEEK
    )
    point_data = calculate_lineup_points(slate_data, POSITIONS, STRUCTURE)

    team_df = member_info_df(SEASON)
    team_df = team_df[['id', 'user_name']].rename(columns={'user_name': 'team_name'})

    chart_actual_vs_optimal(create_lineup_efficiency(point_data, team_df), WEEK)

    # --------------- #
    # SCORE ABOVE AVG #
    # --------------- #
    d = create_opp_difficulty_data(SEASON)
    d.to_csv(f'../outputs/score_above_avg_{SEASON}.csv')
    summarize_opponent_difficulty(d, SEASON)
    chart_opp_difficulty(d, SEASON)

    # ------------ #
    # MAIN METRICS #
    # ------------ #
    schedule_data, teams = fetch_boxscore_data(SEASON)
    draft_pos, rank_df = get_draftpos_rank(SEASON)
    score_df = create_matchup_data(schedule_data)
    team_df = team_df.rename(columns={'id': 'Team_ID', 'team_name': 'Team_Name'})
    team_df['Team_ID'] = team_df['Team_ID'].astype(str)
    full_data = merge_transform_data(score_df, team_df, draft_pos, rank_df)
    full_data.to_excel('../outputs/weekly_score_data.xlsx', index=False)
    print_and_save_charts(full_data, WEEK, WEEK)


if __name__ == '__main__':
    main()