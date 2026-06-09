from src.espn_client import fetch_api_data

team_id_user = {1: 'Jared',
                2: 'Lucas',
                3: 'Prem',
                4: 'Cole',
                5: 'Palak',
                6: 'Jon',
                7: 'Austin',
                8: 'Chris',
                9: 'Casey',
                10: 'MitchB',
                11: 'MitchP',
                12: 'Matt'}

# # Team Name / Owner (2025)
# Tipsy     Jared
# Hej       Lucas
# Gliz      Prem
# Falco     Cole
# Coach     Palak
# Wi Wa     Jon
# Nacua     Austin
# Rec       Chris
# CeeDee    Casey
# Trash     Mitch B
# Dude      Mitch P
# Garg      Matt

def team_id_name(year=2024) -> dict[int: str]:
    """
    pulls team ID and team name

    :return: dict containing "id: team name"
    """
    data = fetch_api_data(views=['mTeam'], year=year)

    team_data = {}
    for team in data['teams']:
        team_data[team['id']] = team['name']

    return team_data
