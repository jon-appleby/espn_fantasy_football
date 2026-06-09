import os
from dotenv import load_dotenv

from src.espn_client import fetch_api_data
from weekly_scripts.act_opt_metrics import compute_pts, get_team_info, chart_oae_pts, transform_data, get_slates
from weekly_scripts.power_ranking import get_player_data, summarize_teams, save_data
from weekly_scripts.score_above_avg import create_data, summarize_data, create_chart
from weekly_scripts.weekly_metrics import fetch_boxscore_data, get_draftpos_rank, create_matchup_data, create_team_data, merge_transform_data, print_and_save_charts

load_dotenv()

league_id = os.getenv('LEAGUE_ID')
positions = ['QB', 'RB', 'WR', 'Flex', 'TE', 'D/ST', 'K']
structure = [1, 2, 2, 1, 1, 1, 1]

season = 2025
week = 8

# ---------------- #
# ACTUAL v OPTIMAL #
# ---------------- #
slate_data = get_slates(
    fetch_api_data(views=['mMatchup', 'mMatchupScore'],
                   year=season,
                   params={'scoringPeriodId': week, 'matchupPeriodId': week}),
                   week_num=week)
point_data = compute_pts(slate_data, positions, structure)
team_df = get_team_info(season, league_id)
chart_oae_pts(transform_data(point_data, team_df), week)

# -------------------- #
# CUSTOM POWER RANKING #
# -------------------- #
# d = get_player_data(season, week)
# t = summarize_teams(d, season, week)
# save_data(t, week, season)

# --------------- #
# SCORE ABOVE AVG #
# --------------- #
d = create_data(season)
d.to_csv(f'../outputs/score_above_avg_{season}.csv')
s = summarize_data(d, season)
create_chart(d, season)

# ------------ #
# MAIN METRICS #
# ------------ #
schedule_data, teams = fetch_boxscore_data(season)
draft_pos, rank_df = get_draftpos_rank(season)
score_df = create_matchup_data(schedule_data)
team_df = create_team_data(teams)
full_data = merge_transform_data(score_df, team_df, draft_pos, rank_df)
print_and_save_charts(full_data, week, week)
full_data.to_excel('/outputs/weekly_score_data.xlsx', index=False)