import os
import pandas as pd
from datetime import datetime as dt

df_dict = {
    'in_season': [],
    'draft': []
}
for root, dirs, files in os.walk('./input'):
    for file in files:
        year = file.split('_')[3]
        f = os.path.join(root, file)
        file_df = pd.read_csv(f).replace('-', 0).fillna(0)
        file_df[['expert', 'group']] = file_df['Expert Name'].str.split(' - ', expand=True)
        file_df.drop(columns=['group', 'Expert Name'], inplace=True)
        file_df.drop_duplicates(inplace=True)
        file_df['max_year'] = int(year)
        file_df['min_year'] = int(year)
        file_df['Rank'].replace({0: 99}, inplace=True)
        file_df['Rank'] = file_df['Rank'].astype(int)

        if 'SeasonToDate' in file:
            df_dict['in_season'].append(file_df)
        elif 'Draft_Accuracy' in file:
            df_dict['draft'].append(file_df)

for group, dfs in df_dict.items():
    data_years = len(dfs)
    current_year = int(dt.today().strftime('%Y'))

    start_df = pd.concat(dfs)

    start_df[['Rank', 'QB', 'RB', 'WR', 'TE', 'K', 'DST', 'IDP']] = (
        start_df[['Rank', 'QB', 'RB', 'WR', 'TE', 'K', 'DST', 'IDP']].astype(int)
    )

    start_df['num_years'] = 1

    # create new df of only experts
    df = start_df['expert'].drop_duplicates().rename('expert').to_frame()

    # add year fields
    df['data_years'] = data_years
    df['current_year'] = current_year

    # get max year
    max_years = start_df.groupby('expert')['max_year'].max().reset_index()
    df = pd.merge(left=df, right=max_years, on='expert', how='left')

    # get min year
    min_years = start_df.groupby('expert')['min_year'].min().reset_index()
    df = pd.merge(left=df, right=min_years, on='expert', how='left')

    # get num years
    num_years = start_df.groupby('expert')['num_years'].count().reset_index()
    df = pd.merge(left=df, right=num_years, on='expert', how='left')

    # get rank
    rank = start_df.groupby('expert')['Rank'].sum().reset_index().rename(columns={'Rank': 'rank_sum'})
    df = pd.merge(left=df, right=rank, on='expert', how='left')

    # remove invalid / NaN
    df.dropna(inplace=True)

    # update types
    df[['max_year', 'min_year', 'num_years', 'rank']] = df[['max_year', 'min_year', 'num_years', 'rank']].astype(int)

    # add extra fields and sort
    df['less_years'] = df['num_years'] - data_years
    df['avg_rank_by_year'] = df['rank_sum'] / df['num_years']

    # filter df
    if group == 'in_season':
        final_df = df.loc[
            (df['num_years'] > 2)  # has at least 3 years of rankings
            &
            (df['max_year'] >= (current_year-1))  # has rankings from the previous year
            &
            (df['rank'] > 0)
        ].reset_index().drop(columns='index')

        final_df.sort_values('avg_rank_by_year', inplace=True)
        final_df = final_df.reset_index().drop(columns='index')

        print('in season expert rankings')
        print(final_df.head(15).to_string(), '\n')

        final_df.to_csv('../Outputs/experts_by_rank_in-season.csv')
    else:
        final_df = df.loc[
            (df['num_years'] > 2)  # has at least 3 years of rankings
            &
            (df['max_year'] > (current_year-2))  # has rankings from 2 years ago
            &
            (df['rank'] > 0)
            ].sort_values('rank').reset_index().drop(columns='index')

        final_df.sort_values('avg_rank_by_year', inplace=True)
        final_df = final_df.reset_index().drop(columns='index')

        print('draft expert rankings')
        print(final_df.head(15).to_string(), '\n')

        final_df.to_csv('../Outputs/experts_by_rank_draft.csv')
