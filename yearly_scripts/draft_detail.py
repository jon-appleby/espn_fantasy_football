from main.espn_api import fetch_api_data
import json
import pandas as pd
import xlwings as xw


def get_draft_data(year):
    """
    get the current draft details from ESPN

    :param year: int: current year
    :return: list of dict of current pick details
    """
    data = fetch_api_data(views=['mMatchup', 'mDraftDetail'], year=year)
    # data = fetch_api_data(views=['mMatchup', 'mDraftDetail'], year=year, league=851935694)

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
    filters = {"players": {"limit": 1500,
                           "sortDraftRanks": {
                               "sortPriority": 100,
                               "sortAsc": True,
                               "value": "STANDARD"
                           }
                           }
               }
    headers = {'x-fantasy-filter': json.dumps(filters)}
    data = fetch_api_data(views=['kona_playercard'], year=year, header=headers)

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
    create updated draft details with an indicator if a player has been drafted

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
    """
    apply formatting by draft status and player position, then save file

    :param year: current draft year
    :param path: path to output file
    :return: none
    """
    updated_data = rankings_drafted(year, path)

    # write to open Excel file, do not save/close
    work_book = xw.Book(path)
    cheat_sheet = work_book.sheets['cheat_sheet_live']
    cheat_sheet.range('A1').value = updated_data.set_index('ECR')

    # apply formatting by draft status
    player_name_range = cheat_sheet.range('B1:B{}'.format(len(updated_data)))
    for cell in player_name_range:
        if cell.offset(0, 4).value:
            cell.color = (192, 0, 0)
        else:
            cell.color = (169, 208, 142)

    # # apply formatting by position
    # for cell in cheat_sheet['C1'].expand('down'):
    #     if cell.value == 'WR':
    #         cell.color = (67, 171, 95)
    #     elif cell.value == 'RB':
    #         cell.color = (73, 112, 196)
    #     elif cell.value == 'TE':
    #         cell.color = (142, 102, 179)
    #     elif cell.value == 'QB':
    #         cell.color = (189, 77, 90)
    #     elif cell.value == 'DST':
    #         cell.color = (153, 124, 92)
    #     elif cell.value == 'K':
    #         cell.color = (168, 168, 168)

    ''' original draft formatting, potentially slightly faster '''
    # apply conditional formatting by draft status
    # for cell in cheat_sheet['F1'].expand('down'):
    #     if cell.value:
    #         cell.color = (169, 208, 142)
    #     else:
    #         cell.color = (192, 0, 0)


if __name__ == '__main__':
    draft_year = 2023
    output_path = './live_draft/live_draft.xlsx'
    update_excel(draft_year, output_path)
