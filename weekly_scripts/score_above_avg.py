import matplotlib.pyplot as plt
import pandas as pd
import dataframe_image as dfi
from weekly_metrics import fetch_boxscore_data, create_matchup_data
from main.team_mapping import team_id_name


def create_data(year):

    def win_loss(row):
        if row['team1_points'] > row['team2_points']:
            return 'w'
        else:
            return 'l'

    schedules, _ = fetch_boxscore_data(year)

    df = create_matchup_data(schedules)
    df.columns = df.columns.str.lower()
    df = df.loc[df['team2_points'] > 0].copy()

    teams = team_id_name(year)
    teams = {str(k): v for k, v in teams.items()}

    df['team1_name'] = df['team1_id'].map(teams)
    df['team2_name'] = df['team2_id'].map(teams)

    df['win/loss'] = df.apply(win_loss, axis=1)

    df['opp_cum_pts'] = df.groupby('team2_id')['team2_points'].cumsum()
    df['opp_cum_weeks'] = df.groupby('team2_id').cumcount() + 1
    df['opp_cum_avg_pts'] = df['opp_cum_pts'] / df['opp_cum_weeks']

    # avg_mapping = df.groupby('team2_id')['team2_points'].mean().reset_index()
    # avg_mapping = avg_mapping.rename(columns={'team2_points': 'opp_total_avg'})
    # avg_mapping = avg_mapping[['team2_id', 'opp_total_avg']]
    # df = pd.merge(left=df, right=avg_mapping, how='left', on='team2_id')

    df = df.drop(columns=['opp_cum_pts', 'opp_cum_weeks'])

    df['opp_avg_diff'] = df['team2_points'] - df['opp_cum_avg_pts']

    df = df.loc[df['opp_avg_diff'] != 0]

    return df


def create_chart(data, year):
    data['color'] = data['win/loss'].map({'w': 'darkgreen', 'l': 'darkred'})

    data['x_group'] = data['team1_name'] + ' - Week ' + data['matchup_period'].astype(str)

    data = data.sort_values(by=['team1_name', 'matchup_period'])

    team_boundaries = data.groupby('team1_name').size().cumsum().values

    plt.figure(figsize=(14, 8))

    bars = plt.bar(data['x_group'], data['opp_avg_diff'], color=data['color'])

    for bar, value in zip(bars, data['opp_avg_diff']):
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
    plt.savefig(f'../Outputs/12-year_{year}_score_above_avg.png', bbox_inches='tight')
    plt.show()


def summarize_data(data: pd.DataFrame, year):
    df = data.drop_duplicates('team1_name')['team1_name']

    data = data.loc[data['opp_avg_diff'] > 0]
    count = data.groupby('team1_name').size().reset_index(name='count')
    avg = data.groupby('team1_name')['opp_avg_diff'].mean().reset_index(name='average')

    df = pd.merge(left=df, right=count, how='left', on='team1_name')
    df = pd.merge(left=df, right=avg, how='left', on='team1_name')
    df['total'] = df['count'] * df['average']
    df = df.sort_values(by='total', ascending=False)
    df = df.rename(columns={'team1_name': 'team'})
    df.index = df['team']
    df = df.drop(columns='team')

    print(df)

    dfi.export(df, f'../Outputs/13-year_{year}_score_above_avg.png')


y = 2024
d = create_data(y)
print(d.to_string())
summarize_data(d, y)
create_chart(d, y)
