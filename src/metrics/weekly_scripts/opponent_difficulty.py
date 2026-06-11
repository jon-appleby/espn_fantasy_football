import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
import dataframe_image as dfi

from metrics.weekly_scripts.chart_utils import set_chart_theme
from metrics.weekly_scripts.weekly_metrics import fetch_boxscore_data, create_matchup_data
from espn.team_mapping import member_info
from espn.espn_client import fetch_api_data


def create_opp_difficulty_data(year):
    def win_loss(row):
        if row['team1_points'] > row['team2_points']:
            return 'w'
        else:
            return 'l'

    schedules, _ = fetch_boxscore_data(year)

    data = create_matchup_data(schedules)

    data.columns = data.columns.str.lower()
    df = data.loc[data['team2_points'] > 0].copy()

    teams = {}
    for member, info in member_info(year).items():
        teams[member] = info['user_name']

    teams = {str(k): v for k, v in teams.items()}

    df['team1_name'] = df['team1_id'].map(teams)
    df['team2_name'] = df['team2_id'].map(teams)

    df['win/loss'] = df.apply(win_loss, axis=1)

    df['opp_cum_pts'] = df.apply(
        lambda row: df[
            (df['team2_id'] == row['team2_id']) &
            (df['matchup_period'] < row['matchup_period'])
            ]['team2_points'].sum(),
        axis=1
    )
    df['opp_cum_weeks'] = df.groupby('team2_id').cumcount()
    df['opp_cum_avg_pts'] = df['opp_cum_pts'] / df['opp_cum_weeks']
    df['opp_avg_diff'] = df['team2_points'] - df['opp_cum_avg_pts']

    return df


def chart_opp_difficulty(data, year):
    """
    Creates two charts:
    1. Heatmap showing opponent points above/below cumulative average by team and week.
    2. Summary bar chart showing average opponent difficulty by team.

    Positive = tougher opponent scoring week.
    Negative = easier/luckier opponent scoring week.
    """
    set_chart_theme()

    df = data.copy()

    # Remove week 1 / invalid rows where prior cumulative average does not exist
    df = df[np.isfinite(df['opp_avg_diff']) & df['opp_avg_diff'].notna()].copy()

    # Sort teams by average opponent difficulty
    summary = (
        df.groupby('team1_name')
        .agg(
            avg_opp_avg_diff=('opp_avg_diff', 'mean'),
            total_opp_avg_diff=('opp_avg_diff', 'sum'),
            weeks=('matchup_period', 'count')
        )
        .reset_index()
        .sort_values('avg_opp_avg_diff', ascending=False)
    )

    team_order = summary['team1_name'].to_list()

    # --------------------- #
    # week-by-week heatmap  #
    # --------------------- #
    heatmap_data = (
        df.pivot_table(
            index='team1_name',
            columns='matchup_period',
            values='opp_avg_diff',
            aggfunc='mean'
        )
        .reindex(team_order)
    )

    max_abs = np.nanmax(np.abs(heatmap_data.to_numpy()))

    fig, ax = plt.subplots(figsize=(12, 6))

    sns.heatmap(
        heatmap_data,
        cmap='RdYlGn_r',
        center=0,
        vmin=-max_abs,
        vmax=max_abs,
        annot=True,
        fmt='.0f',
        linewidths=0.5,
        linecolor='white',
        cbar_kws={'label': 'Opponent points vs cumulative average'},
        ax=ax
    )

    ax.set_title(f'Opponent Difficulty by Week - {year}', fontsize=11)
    ax.set_xlabel('Week', fontsize=9)
    ax.set_ylabel('Team', fontsize=9)
    ax.tick_params(axis='x', labelrotation=0, labelsize=8)
    ax.tick_params(axis='y', labelsize=8)

    plt.tight_layout()
    plt.savefig(f'../outputs/12-year_{year}_opp_difficulty_heatmap.png', bbox_inches='tight')
    plt.show()

    # ------------------------ #
    #  overall summary chart   #
    # ------------------------ #
    summary = summary.sort_values('avg_opp_avg_diff', ascending=True)

    colors = np.where(
        summary['avg_opp_avg_diff'] >= 0,
        '#b22222',  # tougher / unlucky
        '#2e8b57'   # easier / lucky
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(
        summary['team1_name'],
        summary['avg_opp_avg_diff'],
        color=colors
    )

    ax.axvline(0, color='black', linewidth=0.8)
    ax.set_title(f'Average Opponent Difficulty - {year}', fontsize=11)
    ax.set_xlabel('Avg opponent points vs cumulative average', fontsize=9)
    ax.set_ylabel('Team', fontsize=9)
    ax.tick_params(axis='both', labelsize=8)

    for bar in bars:
        value = bar.get_width()
        x_pos = value + 0.5 if value >= 0 else value - 0.5
        ha = 'left' if value >= 0 else 'right'

        ax.text(
            x_pos,
            bar.get_y() + bar.get_height() / 2,
            f'{value:.1f}',
            va='center',
            ha=ha,
            fontsize=8
        )

    ax.text(
        0.99,
        0.02,
        'Positive = tougher opponents / less lucky\nNegative = easier opponents / luckier',
        transform=ax.transAxes,
        fontsize=8,
        color='#666666',
        va='bottom',
        ha='right'
    )

    plt.tight_layout()
    plt.savefig(f'../outputs/14-year_{year}_opp_difficulty_summary.png', bbox_inches='tight')
    plt.show()


def summarize_opponent_difficulty(data: pd.DataFrame, year):
    df = data.drop_duplicates('team1_name')['team1_name']

    data_above = data.loc[data['opp_avg_diff'] > 0]
    count_above = data_above.groupby('team1_name').size().reset_index(name='weeks_above_avg')
    avg_above = data_above.groupby('team1_name')['opp_avg_diff'].mean().reset_index(name='avg_above_avg')

    data_below = data.loc[data['opp_avg_diff'] < 0]
    count_below = data_below.groupby('team1_name').size().reset_index(name='weeks_below_avg')
    avg_below = data_below.groupby('team1_name')['opp_avg_diff'].mean().reset_index(name='avg_below_avg')

    df = pd.merge(left=df, right=count_above, how='left', on='team1_name')
    df = pd.merge(left=df, right=avg_above, how='left', on='team1_name')
    df = df.fillna(0)
    df['total_above'] = df['weeks_above_avg'] * df['avg_above_avg']

    df = pd.merge(left=df, right=count_below, how='left', on='team1_name')
    df = pd.merge(left=df, right=avg_below, how='left', on='team1_name')
    df = df.fillna(0)
    df['total_below'] = df['weeks_below_avg'] * df['avg_below_avg']

    df['above/below_total'] = df['total_above'] + df['total_below']

    df = df.sort_values(by='above/below_total', ascending=False)
    df = df.rename(columns={'team1_name': 'team'})
    df.index = df['team']
    df = df.drop(columns='team')

    # get current rank
    ranks = fetch_api_data(views=['mTeam'], year=year)
    team_ranks = {team['name']: team['rankCalculatedFinal'] for team in ranks['teams']}
    df = df.reset_index()
    df['rank'] = df['team'].map(team_ranks)

    dfi.export(df, f'../outputs/13-year_{year}_score_above_avg.png', table_conversion='matplotlib')

    return df
