from setup_info import SWID, ESPN_S2, LEAGUE_ID
import requests
import pandas as pd
from WeeklyScores import get_draftpos_rank
import time


def iterate_thru_years(max_year, min_year=2018):
    year = 2022
    draft_list = []
    while year <= max_year:
        url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
              f'leagues/{LEAGUE_ID}?view=mMatchup&view=mScoreboard&view=mSettings'
        req = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2})
        data = req.json()

        # iterate through the list and append to dict using index + 1 as team ID
        order = data['settings']['draftSettings']['pickOrder']
        for index, pos in enumerate(order):
            index += 1
            pos_dict = {'year': year,
                        'team_id': str(pos),
                        'draft_pos': index}
            draft_list.append(pos_dict)

        # iterate thru list of teams and get rank + team id
        teams = data['teams']
        for team in teams:
            rank = team['rankCalculatedFinal']
            team_id = team['id']
            rank_dict = {'year': year,
                         'team_id': str(team_id),
                         'rank': rank}
            draft_list.append(rank_dict)

        print(year)
        year += 1
        time.sleep(5)  # sleep 10 secs to avoid over requesting

    data_frame = pd.DataFrame(draft_list)  # TODO: draft_pos or rank fields are null when the other value is populated
    print(data_frame)
    print(draft_list)


if __name__ == '__main__':
    year_end = 2023

    draft_data = iterate_thru_years(year_end)
    # draft_pos, rank_df = get_draftpos_rank(year)
