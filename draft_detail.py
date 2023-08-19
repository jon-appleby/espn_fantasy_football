import json
import pandas as pd
import requests
from setup_info import SWID, ESPN_S2, LEAGUE_ID
import xlwings as xw


def get_draft_data(year):
    """
    get the current draft details from ESPN

    :param year: int: current year
    :return: list of dict of current pick details
    """
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?view=mMatchup&view=mDraftDetail'
    data = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2}).json()

    picks = data['draftDetail']['picks']
    draft_list = [
        {'team': pick['teamId'],
         'player_id': pick['playerId'],
         'round_num': pick['roundId'],
         'round_pick': pick['roundPickNumber'],
         'overall_pick': pick['overallPickNumber']}
        for pick in picks]

    return draft_list


def get_player_card(year):
    """
    get the player details to map to player id

    :param year: current year
    :return: list of dict of player id and player first/last name
    """
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?view=kona_playercard'
    filters = {"players": {"limit": 1500,
                           "sortDraftRanks": {
                               "sortPriority": 100,
                               "sortAsc": True,
                               "value": "STANDARD"
                           }
                           }
               }
    headers = {'x-fantasy-filter': json.dumps(filters)}
    data = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2}, headers=headers).json()

    player_info = data['players']
    player_list = [
        {'player_id': player['player']['id'],
         'first_name': player['player']['firstName'],
         'last_name': player['player']['lastName']}
        for player in player_info]

    return player_list


def get_final_draft_details(year):
    """
    combine draft and player data to map player name

    :param year: current year of draft
    :return: df containing draft pick and player details
    """
    draft = pd.DataFrame(get_draft_data(year))
    player = pd.DataFrame(get_player_card(year))
    draft_df = draft.merge(player, how='left', left_on='player_id', right_on='player_id')

    return draft_df


def rankings_drafted(year, path):
    """
    create updated draft details with an indication if a player has been drafted

    :param year: current year of draft
    :param path: path to ranking details rankings are manually inserted to an Excel file from your fav source (e.g. ESPN ADP)
    :return: new dataframe with player's draft status
    """
    draft_picks = get_final_draft_details(year)
    draft_picks['first_last'] = draft_picks['first_name'] + ' ' + draft_picks['last_name']
    pick_list = draft_picks['first_last'].str.strip().values.tolist()

    rankings = pd.read_excel(path, sheet_name='cheat_sheet_live')

    rankings['Drafted'] = rankings['Player_Name'].str.strip().isin(pick_list)

    return rankings


def update_excel(year, path):
    updated_data = rankings_drafted(year, path)

    # write to open Excel file, do not save/close
    work_book = xw.Book(path)
    cheat_sheet = work_book.sheets['cheat_sheet_live']
    cheat_sheet.range('A1').value = updated_data.set_index('ECR')


if __name__ == '__main__':
    draft_year = 2022
    output_path = './outputs/live_draft.xlsx'
    update_excel(draft_year, output_path)
