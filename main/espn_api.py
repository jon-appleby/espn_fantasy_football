import requests
from main.setup_info import SWID, ESPN_S2, LEAGUE_ID

COOKIES = {"SWID": SWID, "espn_s2": ESPN_S2}


def fetch_api_data(views, year, header=None, params=None, league=LEAGUE_ID):
    """
    pull data from ESPN API using the view & year requested. headers/params are optional

    :param views: list: view (e.g. mMatchup)
    :param year: int: year to pull
    :param header: dict: optional for additional control on limits/filtering
    :param params: dict: optional for additional filtering
    :param league: str: league ID, defaults to my league
    :return: data from api in json format
    """
    url = f'https://fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/' \
          f'leagues/{league}?'

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

    if header and params:
        data = requests.get(url, cookies=COOKIES, headers=header, params=params).json()
    elif header:
        data = requests.get(url, cookies=COOKIES, headers=header).json()
    elif params:
        data = requests.get(url, cookies=COOKIES, params=params).json()
    else:
        data = requests.get(url, cookies=COOKIES).json()

    return data


def fetch_transactions(year):
    url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{LEAGUE_ID}'
           '?view=mStatus'
           '&view=mSettings'
           '&view=mTeam'
           '&view=mTransactions2'
           '&view=modular'
           '&view=mNav')

    data = requests.get(url, cookies=COOKIES).json()

    return data
