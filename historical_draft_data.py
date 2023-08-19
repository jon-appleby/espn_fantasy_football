from setup_info import SWID, ESPN_S2, LEAGUE_ID
import requests
import pandas as pd
import time
import seaborn as sns
import matplotlib.pyplot as plt


def iterate_thru_years(max_year, min_year=2018):
    year = min_year

    combine_df = pd.DataFrame(columns=['year', 'team_id', 'draft_pos', 'rank'])

    while year <= max_year:
        print(f'getting data for {year}')

        url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
              f'leagues/{LEAGUE_ID}?view=mMatchup&view=mScoreboard&view=mSettings'
        req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
        data = req.json()

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

        # iterate thru list of teams and get rank + team id
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
        time.sleep(5)  # sleep x secs to avoid over requesting

    combine_df.to_csv(f'./outputs/historical_draft_data_{min_year}-{max_year}.csv')
    return combine_df


def chart_draft_v_rank(data):
    sns.set_theme(style='darkgrid', palette=None)

    # compare draft pos to rank
    pos_rank = sns.regplot(data=data,
                           x='draft_pos',
                           y='rank',
                           robust=True)
    pos_rank.invert_yaxis()
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    year_end = 2022
    year_start = 2018

    draft_data = iterate_thru_years(year_end, year_start)
    # print(draft_data.head())

    temp_data = pd.read_csv('./outputs/historical_draft_data_2018-2022.csv')
    print(temp_data.to_string())
    chart_draft_v_rank(temp_data)

