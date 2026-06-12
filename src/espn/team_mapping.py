from typing import Any

import pandas as pd

from espn.espn_client import fetch_api_data


def member_info(year=2024) -> dict[Any, Any]:
    """
    Args:
        year (int): year of data
    Returns:
        dict: Team ID: {User's Name, Team Name, User's UID}
    """
    data = fetch_api_data(views=['mTeam'], year=year)

    # create a dict of members & their UIDs
    members_by_id = {}
    for member in data['members']:
        members_by_id[member['id']] = member

    # use member ID (UID) to get first and last names to combine with team name
    team_owner_dict = {}
    for team in data['teams']:
        owner_id = team.get('primaryOwner')
        member = members_by_id.get(owner_id)

        if member is None:
            continue

        user_first = member.get('firstName', '').title()
        user_last = member.get('lastName', '').title()

        if 'mitch' in user_first.lower():
            first_name = f'{user_first[:5]} {user_last[:1]}'
        elif user_first.lower() == 'matthew':
            first_name = 'Matt'
        else:
            first_name = user_first

        team_owner_dict[team['id']] = {
            'user_name': first_name,
            'team_name': team.get('name', ''),
            'user_uid': member['id']
        }

    return team_owner_dict


def member_info_df(year=2024) -> pd.DataFrame:
    members = member_info(year)
    df = pd.DataFrame.from_dict(members, orient='index').reset_index().rename(columns={'index': 'id'})

    return df
