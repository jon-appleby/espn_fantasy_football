import requests
from setup_info import SWID, ESPN_S2, LEAGUE_ID


def fetch_api_data(views, year, header=None):
    """
    pull data from ESPN API using the view & year requested. headers are optional

    :param views: list: view (e.g. mMatchup)
    :param year: int: year to pull
    :param header: dict: optional for additional control on limits/filtering
    :return: data from api in json format
    """
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{LEAGUE_ID}?'

    count = 0
    for v in views:
        count += 1
        if len(views) > 1:
            if count == 1:
                url = url + 'view=' + v
            else:
                url = url + '&view=' + v
        else:
            url = url + 'view=' + v

    if header:
        data = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2}, headers=header).json()
    else:
        data = requests.get(url, cookies={"SWID": SWID, "espn_s2": ESPN_S2}).json()

    return data
