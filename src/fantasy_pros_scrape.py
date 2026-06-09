from selenium import webdriver
from time import sleep
from src.setup_info import FP_USER, FP_PW

year = 2023
week = 2

pos_list = ['flex', 'rb', 'wr', 'qb', 'te']
# url = f'https://www.fantasypros.com/nfl/rankings/ppr-{pos_list[0]}.php'
url = f'https://www.fantasypros.com/nfl/rankings/ppr-{pos_list[0]}.php?signedin'

spec_pos_list = ['qb', 'k', 'dst']
spec_url = f'https://www.fantasypros.com/nfl/rankings/{spec_pos_list[0]}.php'

# open browser in background
options = webdriver.ChromeOptions()
options.add_argument('headless')

# create webdriver object
browser = webdriver.Chrome(executable_path=r'C:\Users\apple\PycharmProjects\chromedriver.exe'
                           # , options=options
                           )
browser.get(url)
browser.maximize_window()

sleep(5)

browser.find_element('xpath', '/html/body/div[2]/div[4]/div/div[1]/div[2]/div[2]/div[3]/div/button[1]/i').click()

# todo: send user/pw info
user = browser.find_element('xpath', '/html/body/src/section[2]/section/section/form/div[1]/div[1]/div')
user.send_keys(FP_USER)
pw = browser.find_element('xpath', '/html/body/src/section[2]/section/section/form/div[1]/div[2]/div')
pw.send_keys(FP_PW)

