import os

from dotenv import load_dotenv
import requests

load_dotenv()

SWID = os.getenv('SWID')
ESPN_S2 = os.getenv('ESPN_S2')
LEAGUE_ID = os.getenv('LEAGUE_ID')
COOKIES = {"SWID": SWID, "espn_s2": ESPN_S2}


def fetch_api_data(views: list, year: int, header: dict = None, params: dict = None, league=LEAGUE_ID):
    """
    pull data from ESPN API using the view & year requested. headers/params are optional

    :param views: view (e.g. mMatchup)
    :param year: year to pull
    :param header: optional for additional control on limits/filtering
    :param params: optional for additional filtering
    :param league: league ID, defaults to my league
    :return: data from api in json format
    """

    url = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{league}?'

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


if __name__ == '__main__':
    print('\nfetch_api_data')
    print(fetch_api_data(['mMatchup'], 2023, league=REDACTED_LEAGUE_ID))

    print('\nfetch_transactions')
    print(fetch_transactions( 2023))
