from main.espn_api import fetch_api_data
import matplotlib.pyplot as plt
import pandas as pd
from main.team_mapping import team_id_mapping
import time
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor


def iterate_thru_years(max_year, min_year=2018):
    year = min_year

    combine_df = pd.DataFrame(columns=['year', 'team_id', 'draft_pos', 'rank'])

    while year <= max_year:
        print(f'getting data for {year}')

        data = fetch_api_data(views=['mScoreboard', 'mSettings'], year=year, )

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

    combine_df.to_csv(f'../outputs/historical_draft_data_{min_year}-{max_year}.csv')
    return combine_df


def chart_draft_v_rank(d):
    sns.set_theme(style='darkgrid', palette=None)

    # compare draft pos to rank
    pos_rank = sns.regplot(data=d,
                           x='draft_pos',
                           y='rank',
                           robust=True)
    pos_rank.invert_yaxis()
    plt.tight_layout()
    plt.show()


def predict_rank(d, curr_year):
    print('\npredicting ranks based on draft pos')

    train_df = d.loc[d['year'] < curr_year]

    # create training and test data
    x_train = train_df[['draft_pos', 'team_id']]
    y_train = train_df['rank']

    # for testing the model
    # test_df = d.loc[d['year'] == curr_year-2]
    # x_test = test_df[['draft_pos', 'team_id']]
    # y_test = test_df['rank']

    # create dataframe of 2024 draft
    draft_pos = pd.DataFrame([{'draft_pos': 1, 'team_id': 8},
                              {'draft_pos': 2, 'team_id': 12},
                              {'draft_pos': 3, 'team_id': 5},
                              {'draft_pos': 4, 'team_id': 10},
                              {'draft_pos': 5, 'team_id': 9},
                              {'draft_pos': 6, 'team_id': 1},
                              {'draft_pos': 7, 'team_id': 4},
                              {'draft_pos': 8, 'team_id': 7},
                              {'draft_pos': 9, 'team_id': 3},
                              {'draft_pos': 10, 'team_id': 6},
                              {'draft_pos': 11, 'team_id': 2},
                              {'draft_pos': 12, 'team_id': 11},
                              ]
                             )

    # create and fit model using training data
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(x_train, y_train)

    # make predictions / test data on test data OR current 2023 draft
    # predictions = model.predict(x_test)
    predictions = pd.DataFrame(model.predict(draft_pos)).rename(columns={0: 'predicted_rank'})

    merged = draft_pos.merge(predictions, how='left', left_index=True, right_index=True)
    merged['team_player_name'] = merged['team_id'].map(team_id_mapping)
    merged.sort_values(by='predicted_rank', inplace=True)
    print(merged)

    # # evaluate model performance
    # mse = mean_squared_error(y_test, predictions)
    # print(f'mse = {mse}')
    #
    # mae = mean_absolute_error(y_test, predictions)
    # print(f'mae = {mae}')


if __name__ == '__main__':
    year_end = 2023
    year_start = 2018
    current_year = 2024

    # data = iterate_thru_years(min_year=year_start, max_year=year_end)

    """replace above 'data' with below file after running to save on API calls"""
    data = pd.read_csv('../Outputs/historical_draft_data_2018-2023.csv')
    chart_draft_v_rank(data)
    predict_rank(data, curr_year=current_year)

