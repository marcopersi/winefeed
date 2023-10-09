import requests
import re

from bs4 import BeautifulSoup

URL = "https://www.sylvies.be/en/auction/226?sort=lotnr_asc&page=2"
page = requests.get(URL)

soup = BeautifulSoup(page.content, "html.parser")

job_elements = soup.find_all("div", class_="row")


for job_element in job_elements:
    innerRows = job_element.find_all("div", class_="row")
    lotNo = job_element.find("p", class_="lot_nr")
    lotEstimate = job_element.find(class_="large-2 columns auction_infos") #estimate
    lotResult = job_element.find(class_="lot_my_bid")
    


    print(lotNo)    
    print(lotEstimate)
    print(lotResult)
    print()
