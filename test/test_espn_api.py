from main.espn_api import fetch_api_data
import json

data = fetch_api_data(views=['mMatchup', 'mMatchupScore'],
                      year=2025,
                      params={'scoringPeriodId': 9, 'matchupPeriodId': 9})


with open('./test_mmatchup_mmatchup_score.json', 'w') as f:
    json.dump(data, f, indent=4)



