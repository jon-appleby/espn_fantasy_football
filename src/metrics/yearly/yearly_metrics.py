import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from espn.constants import SLOT_CODES

MATCHUP_COLUMNS = [
    'year',
    'matchup_period',
    'team_id',
    'manager_id',
    'manager_name',
    'team_name',
    'opp_team_id',
    'opp_manager_id',
    'opp_manager_name',
    'opp_team_name',
    'team_points',
    'opp_points',
    'actual_win',
    'actual_loss',
    'actual_tie',
]

FINISH_COLUMNS = [
    'year',
    'team_id',
    'manager_id',
    'manager_name',
    'team_name',
    'final_rank',
    'championship',
]

ALL_PLAY_COLUMNS = [
    'year',
    'matchup_period',
    'manager_id',
    'manager_name',
    'all_play_wins',
    'all_play_losses',
    'all_play_ties',
]

PROJECTED_ACTUAL_COLUMNS = [
    'year',
    'matchup_period',
    'team_id',
    'manager_id',
    'manager_name',
    'team_name',
    'actual_points',
    'projected_points',
    'projection_diff',
]

BENCH_SLOT_NAMES = {'Bench', 'IR'}


def _format_manager_name(member: dict[str, Any] | None, fallback: str) -> str:
    if not member:
        return fallback

    user_first = member.get('firstName', '').title()
    user_last = member.get('lastName', '').title()

    if 'mitch' in user_first.lower():
        return f'{user_first[:5]} {user_last[:1]}'.strip()
    if user_first.lower() == 'matthew':
        return 'Matt'
    if user_first:
        return user_first
    return fallback


def build_team_lookup(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Map ESPN team ids to stable manager metadata for one season."""

    members_by_id = {
        member.get('id'): member
        for member in data.get('members', [])
        if member.get('id') is not None
    }

    teams = {}
    for team in data.get('teams', []):
        team_id = str(team.get('id'))
        owner_id = team.get('primaryOwner')
        team_name = team.get('name') or f'Team {team_id}'
        manager_name = _format_manager_name(members_by_id.get(owner_id), team_name)

        teams[team_id] = {
            'team_id': team_id,
            'manager_id': str(owner_id or team_id),
            'manager_name': manager_name,
            'team_name': team_name,
            'final_rank': _optional_int(team.get('rankCalculatedFinal')),
        }

    return teams


def is_completed_schedule_matchup(schedule: dict[str, Any]) -> bool:
    """Return True when an ESPN schedule row has two teams and nonzero total score."""

    away = schedule.get('away')
    home = schedule.get('home')
    if not away or not home:
        return False

    away_points = float(away.get('totalPoints') or 0)
    home_points = float(home.get('totalPoints') or 0)
    return away_points + home_points > 0


def is_complete_season(data: dict[str, Any]) -> bool:
    schedules = [
        schedule
        for schedule in data.get('schedule', [])
        if schedule.get('away') and schedule.get('home')
    ]
    return bool(schedules) and all(is_completed_schedule_matchup(schedule) for schedule in schedules)


def normalize_matchup_data(year: int, data: dict[str, Any]) -> pd.DataFrame:
    team_lookup = build_team_lookup(data)
    rows = []

    for schedule in data.get('schedule', []):
        if not is_completed_schedule_matchup(schedule):
            continue

        matchup_period = schedule.get('matchupPeriodId')
        away = schedule['away']
        home = schedule['home']

        matchup_teams = [
            (
                str(away.get('teamId')),
                float(away.get('totalPoints') or 0),
                str(home.get('teamId')),
                float(home.get('totalPoints') or 0),
            ),
            (
                str(home.get('teamId')),
                float(home.get('totalPoints') or 0),
                str(away.get('teamId')),
                float(away.get('totalPoints') or 0),
            ),
        ]

        for team_id, team_points, opp_team_id, opp_points in matchup_teams:
            team = team_lookup.get(team_id, _fallback_team(team_id))
            opponent = team_lookup.get(opp_team_id, _fallback_team(opp_team_id))

            rows.append(
                {
                    'year': year,
                    'matchup_period': matchup_period,
                    'team_id': team_id,
                    'manager_id': team['manager_id'],
                    'manager_name': team['manager_name'],
                    'team_name': team['team_name'],
                    'opp_team_id': opp_team_id,
                    'opp_manager_id': opponent['manager_id'],
                    'opp_manager_name': opponent['manager_name'],
                    'opp_team_name': opponent['team_name'],
                    'team_points': team_points,
                    'opp_points': opp_points,
                    'actual_win': int(team_points > opp_points),
                    'actual_loss': int(team_points < opp_points),
                    'actual_tie': int(team_points == opp_points),
                }
            )

    return pd.DataFrame(rows, columns=MATCHUP_COLUMNS)


def normalize_finish_data(year: int, data: dict[str, Any], count_championships: bool = True) -> pd.DataFrame:
    team_lookup = build_team_lookup(data)
    rows = []

    for team in team_lookup.values():
        final_rank = team.get('final_rank')
        championship = int(count_championships and final_rank == 1)
        rows.append(
            {
                'year': year,
                'team_id': team['team_id'],
                'manager_id': team['manager_id'],
                'manager_name': team['manager_name'],
                'team_name': team['team_name'],
                'final_rank': final_rank,
                'championship': championship,
            }
        )

    return pd.DataFrame(rows, columns=FINISH_COLUMNS)


def fetch_historical_matchup_data(
        start_year: int,
        end_year: int,
        pause_seconds: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pull and normalize yearly matchup and finish data from ESPN.

    Only fully-completed seasons are included. A season with any
    unplayed week (e.g. upcoming season before it starts, or still
    in progress) is skipped via is_complete_season(), so callers
    never have partial season data leaking into all-time
    stats. end_year is just the upper bound to check up to; the actual last
    included year may be earlier (see matchup_df['year'].max()).
    """

    from espn.espn_client import fetch_api_data

    matchups = []
    finishes = []

    for year in range(start_year, end_year + 1):
        print(f'getting yearly matchup data for {year}')
        try:
            data = fetch_api_data(views=['mBoxscore', 'mTeam'], year=year)
        except Exception as exc:
            if year == end_year:
                print(f'skipping {year}: {exc}')
                continue
            raise

        if not is_complete_season(data):
            print(f'skipping {year}: season not fully complete yet')
            continue

        matchups.append(normalize_matchup_data(year, data))
        finishes.append(normalize_finish_data(year, data, count_championships=True))

        if pause_seconds:
            time.sleep(pause_seconds)

    matchup_df = pd.concat(matchups, ignore_index=True) if matchups else pd.DataFrame(columns=MATCHUP_COLUMNS)
    finish_df = pd.concat(finishes, ignore_index=True) if finishes else pd.DataFrame(columns=FINISH_COLUMNS)

    return matchup_df, finish_df


def calculate_all_play_records(matchups: pd.DataFrame) -> pd.DataFrame:
    if matchups.empty:
        return pd.DataFrame(columns=ALL_PLAY_COLUMNS)

    rows = []
    for (year, matchup_period), week in matchups.groupby(['year', 'matchup_period'], sort=True):
        week = week.drop_duplicates('manager_id')

        for _, team in week.iterrows():
            opponents = week.loc[week['manager_id'] != team['manager_id']]
            rows.append(
                {
                    'year': year,
                    'matchup_period': matchup_period,
                    'manager_id': team['manager_id'],
                    'manager_name': team['manager_name'],
                    'all_play_wins': int((team['team_points'] > opponents['team_points']).sum()),
                    'all_play_losses': int((team['team_points'] < opponents['team_points']).sum()),
                    'all_play_ties': int((team['team_points'] == opponents['team_points']).sum()),
                }
            )

    return pd.DataFrame(rows, columns=ALL_PLAY_COLUMNS)


def create_all_time_summary(matchups: pd.DataFrame, finishes: pd.DataFrame | None = None) -> pd.DataFrame:
    if matchups.empty:
        return _empty_summary()

    matchups = matchups.sort_values(['year', 'matchup_period', 'manager_name']).copy()
    actual = (
        matchups
        .groupby('manager_id', as_index=False)
        .agg(
            manager_name=('manager_name', 'last'),
            seasons_played=('year', 'nunique'),
            games_played=('matchup_period', 'count'),
            actual_wins=('actual_win', 'sum'),
            actual_losses=('actual_loss', 'sum'),
            actual_ties=('actual_tie', 'sum'),
            points_for=('team_points', 'sum'),
            points_against=('opp_points', 'sum'),
        )
    )

    all_play = calculate_all_play_records(matchups)
    all_play_summary = (
        all_play
        .groupby('manager_id', as_index=False)
        .agg(
            all_play_wins=('all_play_wins', 'sum'),
            all_play_losses=('all_play_losses', 'sum'),
            all_play_ties=('all_play_ties', 'sum'),
        )
    )

    summary = actual.merge(all_play_summary, on='manager_id', how='left')

    if finishes is not None and not finishes.empty:
        championships = (
            finishes
            .groupby('manager_id', as_index=False)
            .agg(championships=('championship', 'sum'))
        )
        summary = summary.merge(championships, on='manager_id', how='left')
    else:
        summary['championships'] = 0

    summary = summary.fillna(
        {
            'all_play_wins': 0,
            'all_play_losses': 0,
            'all_play_ties': 0,
            'championships': 0,
        }
    )

    int_columns = [
        'seasons_played',
        'games_played',
        'actual_wins',
        'actual_losses',
        'actual_ties',
        'all_play_wins',
        'all_play_losses',
        'all_play_ties',
        'championships',
    ]
    summary[int_columns] = summary[int_columns].astype(int)

    summary['actual_games'] = summary['actual_wins'] + summary['actual_losses'] + summary['actual_ties']
    summary['all_play_games'] = summary['all_play_wins'] + summary['all_play_losses'] + summary['all_play_ties']
    summary['actual_win_pct'] = _record_pct(summary['actual_wins'], summary['actual_ties'], summary['actual_games'])
    summary['all_play_win_pct'] = _record_pct(
        summary['all_play_wins'],
        summary['all_play_ties'],
        summary['all_play_games'],
    )
    summary['actual_record'] = summary.apply(
        lambda row: _format_record(row['actual_wins'], row['actual_losses'], row['actual_ties']),
        axis=1,
    )
    summary['all_play_record'] = summary.apply(
        lambda row: _format_record(row['all_play_wins'], row['all_play_losses'], row['all_play_ties']),
        axis=1,
    )

    summary = summary.sort_values(
        ['all_play_win_pct', 'championships', 'actual_win_pct', 'points_for'],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    summary['overall_rank'] = summary.index + 1

    return summary[
        [
            'overall_rank',
            'manager_id',
            'manager_name',
            'seasons_played',
            'championships',
            'games_played',
            'actual_record',
            'actual_wins',
            'actual_losses',
            'actual_ties',
            'actual_win_pct',
            'all_play_record',
            'all_play_wins',
            'all_play_losses',
            'all_play_ties',
            'all_play_games',
            'all_play_win_pct',
            'points_for',
            'points_against',
        ]
    ]


def create_head_to_head_records(matchups: pd.DataFrame) -> pd.DataFrame:
    if matchups.empty:
        return pd.DataFrame(
            columns=[
                'manager_id',
                'manager_name',
                'opp_manager_id',
                'opp_manager_name',
                'wins',
                'losses',
                'ties',
                'games',
                'win_pct',
                'record',
            ]
        )

    records = (
        matchups
        .groupby(['manager_id', 'manager_name', 'opp_manager_id', 'opp_manager_name'], as_index=False)
        .agg(
            wins=('actual_win', 'sum'),
            losses=('actual_loss', 'sum'),
            ties=('actual_tie', 'sum'),
        )
    )
    records[['wins', 'losses', 'ties']] = records[['wins', 'losses', 'ties']].astype(int)
    records['games'] = records['wins'] + records['losses'] + records['ties']
    records['win_pct'] = _record_pct(records['wins'], records['ties'], records['games'])
    records['record'] = records.apply(lambda row: _format_record(row['wins'], row['losses'], row['ties']), axis=1)

    return records


def normalize_projected_actual_week(
        year: int,
        matchup_period: int,
        data: dict[str, Any],
        team_lookup: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    if team_lookup is None:
        team_lookup = build_team_lookup(data)

    rows = []
    for team in data.get('teams', []):
        team_id = str(team.get('id'))
        team_info = team_lookup.get(team_id, _fallback_team(team_id))
        roster = team.get('roster', {}).get('entries', [])
        actual_points = 0.0
        projected_points = 0.0

        for player_entry in roster:
            slot_name = SLOT_CODES.get(player_entry.get('lineupSlotId'), 'Unknown')
            if slot_name in BENCH_SLOT_NAMES:
                continue

            actual, projected = _player_week_points(player_entry, matchup_period)
            actual_points += actual
            projected_points += projected

        rows.append(
            {
                'year': year,
                'matchup_period': matchup_period,
                'team_id': team_id,
                'manager_id': team_info['manager_id'],
                'manager_name': team_info['manager_name'],
                'team_name': team_info['team_name'],
                'actual_points': actual_points,
                'projected_points': projected_points,
                'projection_diff': actual_points - projected_points,
            }
        )

    return pd.DataFrame(rows, columns=PROJECTED_ACTUAL_COLUMNS)


def fetch_projected_actual_data(matchups: pd.DataFrame, pause_seconds: float = 1.0) -> pd.DataFrame:
    """Pull submitted-starter actual and projected points for each completed week."""

    if matchups.empty:
        return pd.DataFrame(columns=PROJECTED_ACTUAL_COLUMNS)

    from espn.espn_client import fetch_api_data

    rows = []
    year_team_lookup = {
        year: _team_lookup_from_matchups(year_matchups)
        for year, year_matchups in matchups.groupby('year')
    }

    completed_weeks = (
        matchups[['year', 'matchup_period']]
        .drop_duplicates()
        .sort_values(['year', 'matchup_period'])
    )

    for row in completed_weeks.itertuples(index=False):
        year = int(row.year)
        matchup_period = int(row.matchup_period)
        print(f'getting projected vs actual data for {year} week {matchup_period}')
        try:
            data = fetch_api_data(
                views=['mMatchup', 'mMatchupScore'],
                year=year,
                params={'scoringPeriodId': matchup_period, 'matchupPeriodId': matchup_period},
            )
        except Exception as exc:
            print(f'skipping projected vs actual for {year} week {matchup_period}: {exc}')
            continue

        rows.append(
            normalize_projected_actual_week(
                year=year,
                matchup_period=matchup_period,
                data=data,
                team_lookup=year_team_lookup.get(year),
            )
        )

        if pause_seconds:
            time.sleep(pause_seconds)

    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=PROJECTED_ACTUAL_COLUMNS)


def summarize_projected_vs_actual(projected_actual: pd.DataFrame) -> pd.DataFrame:
    if projected_actual.empty:
        return pd.DataFrame(
            columns=[
                'manager_id',
                'manager_name',
                'weeks',
                'actual_points',
                'projected_points',
                'projection_diff',
                'actual_vs_projected_pct',
            ]
        )

    summary = (
        projected_actual
        .sort_values(['year', 'matchup_period', 'manager_name'])
        .groupby('manager_id', as_index=False)
        .agg(
            manager_name=('manager_name', 'last'),
            weeks=('matchup_period', 'count'),
            actual_points=('actual_points', 'sum'),
            projected_points=('projected_points', 'sum'),
        )
    )
    summary['projection_diff'] = summary['actual_points'] - summary['projected_points']
    summary['actual_vs_projected_pct'] = np.where(
        summary['projected_points'] > 0,
        summary['actual_points'] / summary['projected_points'],
        0,
    )

    return summary.sort_values('actual_points', ascending=False).reset_index(drop=True)


def print_and_save_yearly_charts(
        summary: pd.DataFrame,
        head_to_head: pd.DataFrame,
        projected_actual: pd.DataFrame,
        output_dir: str | Path,
        start_year: int,
        end_year: int,
) -> None:
    output_dir = Path(output_dir)
    year_label = f'{start_year}-{end_year}'

    chart_overall_ranking(summary, output_dir / f'all_time_overall_ranking_{year_label}.png')
    # chart_actual_vs_all_play(summary, output_dir / f'all_time_actual_vs_all_play_{year_label}.png')
    chart_head_to_head_heatmap(head_to_head, summary, output_dir / f'all_time_head_to_head_{year_label}.png')
    chart_scoring_overview(summary, projected_actual, output_dir / f'all_time_scoring_overview_{year_label}.png')


def chart_overall_ranking(summary: pd.DataFrame, path: str | Path | None = None) -> None:
    if summary.empty:
        return

    plt, _, chart_fonts, save_chart_func, set_chart_theme_func = _chart_helpers()
    set_chart_theme_func(style="darkgrid")
    data = summary.copy()

    bubble_color = '#1c6689'
    min_size, size_step = 150, 260  # points^2 per championship

    sizes = min_size + data['championships'] * size_step

    # axis limits fit to the data, not a fixed 0-1 range
    x_min, x_max = data['actual_win_pct'].min() - 0.02, data['actual_win_pct'].max() + 0.02
    y_min, y_max = data['all_play_win_pct'].min() - 0.02, data['all_play_win_pct'].max() + 0.02

    fig, ax = plt.subplots(figsize=(11, 6.5))

    # reference line where all-play and actual win rates match
    ref_min, ref_max = min(x_min, y_min), max(x_max, y_max)
    ax.plot([ref_min, ref_max], [ref_min, ref_max], color='#b0b0b0', linewidth=1, linestyle='--', zorder=1)


    ax.scatter(
        data['actual_win_pct'],
        data['all_play_win_pct'],
        s=sizes,
        color=bubble_color,
        alpha=0.75,
        edgecolors='#262626',
        linewidths=0.8,
        zorder=3,
    )

    for _, row in data.iterrows():
        ax.annotate(
            row['manager_name'],
            xy=(row['actual_win_pct'], row['all_play_win_pct']),
            xytext=(0, 9),
            textcoords='offset points',
            ha='center',
            va='bottom',
            fontsize=chart_fonts['data_label'],
            color='#262626',
        )

    ax.set_title(
        'All-Time Overall Ranking: All-Play vs Actual Win Rate (bubble size = championships)',
        fontsize=chart_fonts['title'],
    )
    ax.set_xlabel('Actual win percentage', fontsize=chart_fonts['label'])
    ax.set_ylabel('All-play win percentage', fontsize=chart_fonts['label'])

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    ax.tick_params(axis='both', labelsize=chart_fonts['tick'])

    champ_values = sorted(data['championships'].unique())
    legend_handles = [
        Line2D(
            [0], [0],
            marker='o',
            color='none',
            markerfacecolor=bubble_color,
            markeredgecolor='#262626',
            alpha=0.75,
            markersize=np.sqrt(min_size + c * size_step) / 2,
            label=f'{int(c)} title{"s" if c != 1 else ""}',
        )
        for c in champ_values
    ]
    ax.legend(
        handles=legend_handles,
        title='Championships',
        fontsize=chart_fonts['legend'],
        title_fontsize=chart_fonts['legend'],
        loc='upper left',
        bbox_to_anchor=(1.01, 1.0),
        borderaxespad=0,
    )

    save_chart_func(path, fig=fig)


def chart_scoring_overview(
        summary: pd.DataFrame,
        projected_actual: pd.DataFrame,
        path: str | Path | None = None,
) -> None:
    """Combined points for / points against / projected points, three dots per team."""
    if summary.empty or projected_actual.empty:
        return

    plt, _, chart_fonts, save_chart_func, set_chart_theme_func = _chart_helpers()
    set_chart_theme_func(style="darkgrid")

    data = summary.merge(
        projected_actual[['manager_id', 'projected_points']],
        on='manager_id',
        how='left',
    )
    data = data.sort_values('points_for', ascending=True).copy()

    metric_colors = {
        'points_for': '#1c6689',        # teal
        'points_against': '#9c3b32',    # maroon
        'projected_points': '#6a3d9a',  # purple
    }
    metric_labels = {
        'points_for': 'Points for',
        'points_against': 'Points against',
        'projected_points': 'Projected',
    }
    metrics = list(metric_colors)

    values = data[metrics].to_numpy(dtype=float)
    min_val = values.min(axis=1)
    max_val = values.max(axis=1)

    fig, ax = plt.subplots(figsize=(11, max(6.5, len(data) * 0.45)))
    ax.hlines(
        y=data['manager_name'],
        xmin=min_val,
        xmax=max_val,
        color='#b0b0b0',
        linewidth=3,
        zorder=1,
    )

    for metric in metrics:
        ax.scatter(
            data[metric],
            data['manager_name'],
            color=metric_colors[metric],
            zorder=3,
            label=metric_labels[metric],
        )

    # value labels: left of the min dot, right of the max dot, above the middle dot (no delta label)
    for _, row in data.iterrows():
        lo, mid, hi = sorted(metrics, key=lambda m: row[m])

        ax.annotate(
            f'{row[lo]:,.0f}',
            xy=(row[lo], row['manager_name']),
            xytext=(-8, 0),
            textcoords='offset points',
            ha='right',
            va='center',
            fontsize=chart_fonts['data_label'],
            color='#555555',
        )
        ax.annotate(
            f'{row[hi]:,.0f}',
            xy=(row[hi], row['manager_name']),
            xytext=(8, 0),
            textcoords='offset points',
            ha='left',
            va='center',
            fontsize=chart_fonts['data_label'],
            color='#555555',
        )
        ax.annotate(
            f'{row[mid]:,.0f}',
            xy=(row[mid], row['manager_name']),
            xytext=(0, 8),
            textcoords='offset points',
            ha='center',
            va='bottom',
            fontsize=chart_fonts['data_label'],
            color='#555555',
        )

    ax.set_title('All-Time Points For / Against / Projected', fontsize=chart_fonts['title'])
    ax.set_xlabel('Total points', fontsize=chart_fonts['label'])
    ax.set_ylabel('')
    ax.tick_params(axis='both', labelsize=chart_fonts['tick'])
    ax.legend(fontsize=chart_fonts['legend'])

    save_chart_func(path, fig=fig)


def chart_actual_vs_all_play(summary: pd.DataFrame, path: str | Path | None = None) -> None:
    if summary.empty:
        return

    plt, _, chart_fonts, save_chart_func, set_chart_theme_func = _chart_helpers()
    set_chart_theme_func(style="darkgrid")
    data = summary.sort_values('all_play_win_pct', ascending=True).copy()

    fig, ax = plt.subplots(figsize=(11, max(6.5, len(data) * 0.45)))
    ax.barh(data['manager_name'], data['all_play_win_pct'], color='#1c6689', label='All-play', alpha=0.9)
    ax.barh(data['manager_name'], data['actual_win_pct'], color='#b0b0b0', label='Actual', alpha=0.7)

    for _, row in data.iterrows():
        diff = row['actual_win_pct'] - row['all_play_win_pct']
        text = f'{diff:+.1%}'
        ax.annotate(
            text,
            xy=(max(row['actual_win_pct'], row['all_play_win_pct']), row['manager_name']),
            xytext=(6, 0),
            textcoords='offset points',
            va='center',
            ha='left',
            fontsize=chart_fonts['data_label'],
            color='#262626',
        )

    ax.set_title('Actual Win Rate vs All-Play Win Rate', fontsize=chart_fonts['title'])
    ax.set_xlabel('Win percentage', fontsize=chart_fonts['label'])
    ax.set_ylabel('')
    ax.set_xlim(0, 1)
    ax.tick_params(axis='both', labelsize=chart_fonts['tick'])
    ax.legend(fontsize=chart_fonts['legend'], loc='lower right')

    save_chart_func(path, fig=fig)


def chart_head_to_head_heatmap(
        head_to_head: pd.DataFrame,
        summary: pd.DataFrame,
        path: str | Path | None = None,
) -> None:
    if head_to_head.empty or summary.empty:
        return

    plt, sns, chart_fonts, save_chart_func, set_chart_theme_func = _chart_helpers()
    set_chart_theme_func(style="white")
    manager_order = summary.sort_values('overall_rank')['manager_name'].to_list()

    heatmap_data = (
        head_to_head
        .pivot_table(index='manager_name', columns='opp_manager_name', values='win_pct', aggfunc='mean')
        .reindex(index=manager_order, columns=manager_order)
    )
    annotations = (
        head_to_head
        .pivot_table(index='manager_name', columns='opp_manager_name', values='record', aggfunc='first')
        .reindex(index=manager_order, columns=manager_order)
        .fillna('')
    )

    for manager in manager_order:
        if manager in heatmap_data.index and manager in heatmap_data.columns:
            heatmap_data.loc[manager, manager] = np.nan
            annotations.loc[manager, manager] = ''

    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        heatmap_data,
        cmap='RdYlGn',
        center=0.5,
        vmin=0,
        vmax=1,
        annot=annotations,
        fmt='',
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label': 'Head-to-head win percentage'},
        ax=ax,
    )
    ax.set_title('All-Time Head-to-Head Records', fontsize=chart_fonts['title'])
    ax.set_xlabel('Opponent', fontsize=chart_fonts['label'])
    ax.set_ylabel('Manager', fontsize=chart_fonts['label'])
    ax.tick_params(axis='x', labelrotation=45, labelsize=chart_fonts['tick'])
    ax.tick_params(axis='y', labelrotation=0, labelsize=chart_fonts['tick'])

    save_chart_func(path, fig=fig)


def _fallback_team(team_id: str) -> dict[str, Any]:
    return {
        'team_id': team_id,
        'manager_id': team_id,
        'manager_name': f'Team {team_id}',
        'team_name': f'Team {team_id}',
        'final_rank': None,
    }


def _optional_int(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _chart_helpers():
    import matplotlib.pyplot as plt
    import seaborn as sns

    from metrics.weekly.chart_utils import CHART_FONTS, save_chart, set_chart_theme

    return plt, sns, CHART_FONTS, save_chart, set_chart_theme


def _record_pct(wins: pd.Series, ties: pd.Series, games: pd.Series) -> pd.Series:
    return pd.Series(np.where(games > 0, (wins + (0.5 * ties)) / games, 0), index=wins.index)


def _format_record(wins: int, losses: int, ties: int) -> str:
    if ties:
        return f'{int(wins)}-{int(losses)}-{int(ties)}'
    return f'{int(wins)}-{int(losses)}'


def _empty_summary() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            'overall_rank',
            'manager_id',
            'manager_name',
            'seasons_played',
            'championships',
            'games_played',
            'actual_record',
            'actual_wins',
            'actual_losses',
            'actual_ties',
            'actual_win_pct',
            'all_play_record',
            'all_play_wins',
            'all_play_losses',
            'all_play_ties',
            'all_play_games',
            'all_play_win_pct',
            'points_for',
            'points_against',
        ]
    )


def _player_week_points(player_entry: dict[str, Any], matchup_period: int) -> tuple[float, float]:
    actual = 0.0
    projected = 0.0
    player = player_entry.get('playerPoolEntry', {}).get('player', {})

    for stat in player.get('stats', []):
        if stat.get('scoringPeriodId') != matchup_period:
            continue

        applied_total = float(stat.get('appliedTotal') or 0)
        if stat.get('statSourceId') == 0:
            actual = applied_total
        elif stat.get('statSourceId') == 1:
            projected = applied_total

    return actual, projected


def _team_lookup_from_matchups(matchups: pd.DataFrame) -> dict[str, dict[str, Any]]:
    teams = (
        matchups[['team_id', 'manager_id', 'manager_name', 'team_name']]
        .drop_duplicates('team_id')
        .to_dict('records')
    )

    return {
        str(team['team_id']): {
            'team_id': str(team['team_id']),
            'manager_id': team['manager_id'],
            'manager_name': team['manager_name'],
            'team_name': team['team_name'],
        }
        for team in teams
    }