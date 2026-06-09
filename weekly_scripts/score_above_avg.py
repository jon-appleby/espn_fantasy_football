import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import dataframe_image as dfi
from weekly_scripts.weekly_metrics import fetch_boxscore_data, create_matchup_data
from src.team_mapping import team_id_name
from src.espn_api import fetch_api_data


def create_data(year):
    def win_loss(row):
        if row['team1_points'] > row['team2_points']:
            return 'w'
        else:
            return 'l'

    schedules, _ = fetch_boxscore_data(year)

    data = create_matchup_data(schedules)

    data.columns = data.columns.str.lower()
    df = data.loc[data['team2_points'] > 0].copy()

    teams = team_id_name(year)
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

    # filtered = df.loc[df['team2_id'] == '2']
    # print(filtered.to_string())

    return df


def create_chart(data, year):
    df = data.loc[data['opp_avg_diff'] != 0].copy()

    df = df[np.isfinite(df['opp_avg_diff']) & df['opp_avg_diff'].notna()]
    df['color'] = df['win/loss'].map({'w': 'darkgreen', 'l': 'darkred'})

    df['x_group'] = df['team1_name'] + ' - Week ' + df['matchup_period'].astype(str)

    df = df.sort_values(by=['team1_name', 'matchup_period'])

    team_boundaries = df.groupby('team1_name').size().cumsum().values

    plt.figure(figsize=(14, 8))

    bars = plt.bar(df['x_group'], df['opp_avg_diff'], color=df['color'])

    for bar, value in zip(bars, df['opp_avg_diff']):
        y_pos = bar.get_height() + 2 if value > 0 else bar.get_height() - 4
        plt.text(bar.get_x() + bar.get_width() / 2, y_pos, f'{value:.1f}',
                 ha='center', va='bottom', fontsize=6, color='black', rotation=90)

    for boundary in team_boundaries[:-1]:
        plt.axvline(boundary - 0.5, color='black', linestyle='-', linewidth=1)

    plt.xlabel('Team & Matchup Period', fontsize=9)
    plt.ylabel('Opponent Difference from Cumulative Average', fontsize=9)
    plt.xticks(fontsize=8, rotation=90)
    plt.yticks(fontsize=8)
    plt.axhline(0, color='black', linewidth=0.8, linestyle='--')

    plt.legend(handles=[
        plt.Line2D([0], [0], color='darkgreen', lw=4, label='Win'),
        plt.Line2D([0], [0], color='darkred', lw=4, label='Loss')
    ], loc='upper left')

    plt.tight_layout()
    plt.savefig(f'./Outputs/12-year_{year}_score_above_avg.png', bbox_inches='tight')
    plt.show()


def summarize_data(data: pd.DataFrame, year):
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
    ranks = fetch_api_data(views=['mTeam'], year=2025)
    team_ranks = {team['name']: team['currentProjectedRank'] for team in ranks['teams']}
    df = df.reset_index()
    df['rank'] = df['team'].map(team_ranks)

    dfi.export(df, f'./Outputs/13-year_{year}_score_above_avg.png', table_conversion='matplotlib')

    return df

if __name__ == '__main__':
    y = 2025
    w = 17
    d = create_data(y)
    print(d.to_string())
    d.to_csv(f'../Outputs/Testing/score_above_avg_{y}.csv')
    s = summarize_data(d, y)
    print(s.to_string())
    create_chart(d, y)
