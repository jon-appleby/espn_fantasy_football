import requests
import pandas as pd
from bs4 import BeautifulSoup

year = 2023
week = 2

pos_list = ['flex', 'rb', 'wr', 'qb', 'te']
url = f'https://www.fantasypros.com/nfl/rankings/ppr-{pos_list[0]}.php'

spec_pos_list = ['qb', 'k', 'dst']
spec_url = f'https://www.fantasypros.com/nfl/rankings/{spec_pos_list[0]}.php'

req = requests.get(url, headers={"ranking_type_name": "weekly",
                                 "year": str(year),
                                 "week": str(week),
                                 "scoring": "PPR"})
data = req.text

# print(req.headers)

soup = BeautifulSoup(data, features='lxml')

print(soup.prettify())
