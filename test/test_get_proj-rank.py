from main.espn_api import fetch_api_data
import json

data = fetch_api_data(views=['mTeam'], params={'matchupPeriodId': 8}, year=2025)
with open('./test_get_proj-rank.json', 'w') as f:
    json.dump(data, f, indent=4)

team_ranks = {team['name']: team['currentProjectedRank'] for team in data['teams']}
# for team in data['teams']:
#     team_ranks[team['name']] = team['currentProjectedRank']

print(team_ranks)

