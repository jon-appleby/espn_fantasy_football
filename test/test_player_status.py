import requests as requests
from bs4 import BeautifulSoup
import pandas as pd

# https://www.prosportstransactions.com/football/Search/SearchResults.php
# ?Player=&Team=&BeginDate=2024-08-01&EndDate=2024-12-31&InjuriesChkBx=yes&PersonalChkBx=yes&submit=Search

week = 7
year = 2024
url = f'https://www.nfl.com/injuries/league/{year}/reg{week}'

i = 1
for _ in range(14):
    print(i)
    i += 1

# df_list = pd.read_html(url)
# df = pd.concat(df_list).fillna('')
# print(df.to_string())

# response = requests.get(url)
# print(response.text)
# soup = BeautifulSoup(responsez.content, 'html.parser')
# print(soup.prettify())
# table = soup.find('table', attrs={'class': 'd3-o-table d3-o-table--detailed d3-o-reports--detailed'})

# data = []
# table_body = table.find('tbody')
# rows = table_body.find_all('tr')
# for row in rows:
#     data.append([element.text.strip() for element in row.find_all('td')])
#
# print(data)
#
# data_header = []
# table_headers = table.find('thead')
# row_headers = table_headers.find_all('tr')
# for row in row_headers:
#     data_header.append([element.text.strip() for element in row.find_all('th')])
#
# print(data_header)
#
# df = pd.DataFrame(columns=data_header, data=data)
# print(df.to_string())
