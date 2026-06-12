import os

import requests
from dotenv import load_dotenv

load_dotenv()

SWID = os.getenv('SWID')
ESPN_S2 = os.getenv('ESPN_S2')
LEAGUE_ID = os.getenv('LEAGUE_ID')
COOKIES = {"SWID": SWID, "espn_s2": ESPN_S2}


def fetch_api_data(
        views: list,
        year: int,
        header: dict | None = None,
        params: dict | None = None
):
    """
    pull data from ESPN API using the view & year requested. headers/params are optional

    :param views: view (e.g. mMatchup)
    :param year: year to pull
    :param header: optional for additional control on limits/filtering
    :param params: optional for additional filtering
    :return: data from api in json format
    """

    url = (
        f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/'
        f'seasons/{year}/segments/0/leagues/{LEAGUE_ID}'
    )

    query_params = [('view', view) for view in views]

    if params:
        query_params.extend(params.items())

    response = requests.get(
        url,
        headers=header,
        params=query_params,
        cookies=COOKIES,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


def fetch_transactions(year):
    url = (f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{year}/segments/0/leagues/{LEAGUE_ID}'
           '?view=mStatus'
           '&view=mSettings'
           '&view=mTeam'
           '&view=mTransactions2'
           '&view=modular'
           '&view=mNav')

    return requests.get(url, cookies=COOKIES).json()
