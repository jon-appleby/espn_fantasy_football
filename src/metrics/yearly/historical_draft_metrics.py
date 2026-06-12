import time

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from espn.espn_client import fetch_api_data


def iterate_thru_years(max_year, min_year=2018):
    year = min_year

    combine_df = pd.DataFrame(columns=['year', 'team_id', 'draft_pos', 'rank'])

    while year <= max_year:
        print(f'getting data for {year}')

        data = fetch_api_data(views=['mScoreboard', 'mSettings'], year=year)

        # iterate through the list and append to dict using index + 1 as team ID
        draft_list = []
        order = data['settings']['draftSettings']['pickOrder']
        for index, pos in enumerate(order):
            index += 1
            pos_dict = {'year': year,
                        'team_id': str(pos),
                        'draft_pos': float(index)}
            draft_list.append(pos_dict)
        draft_df = pd.DataFrame(draft_list)

        # iterate through list of teams and get rank + team id
        rank_list = []
        teams = data['teams']
        for team in teams:
            rank = team['rankCalculatedFinal']
            team_id = team['id']
            rank_dict = {'year': year,
                         'team_id': str(team_id),
                         'rank': float(rank)}
            rank_list.append(rank_dict)
        rank_df = pd.DataFrame(rank_list)

        # merge the dataframes created in above loops
        merge_df = draft_df.merge(rank_df, left_on=['year', 'team_id'], right_on=['year', 'team_id'])
        # combine the new df to the blank df created before while loop
        combine_df = pd.concat([combine_df, merge_df], sort=False, ignore_index=True)

        year += 1
        time.sleep(3)  # sleep x secs to avoid over requesting

    combine_df.to_csv(fr'C:/Users/apple/PythonProjects/espn_fantasy_football/outputs/historical_draft_data_{min_year}-{max_year}.csv')

    return combine_df


def chart_draft_v_rank(d):
    sns.set_theme(style='darkgrid', palette=None)

    # compare draft pos to rank
    pos_rank = sns.regplot(
        data=d,
        x='draft_pos',
        y='rank',
        # robust=True
    )
    pos_rank.invert_yaxis()
    plt.tight_layout()
    plt.show()
