from paiper.scraper import Scraper
from progress.bar import ChargingBar
from bs4 import BeautifulSoup
import requests
import json
import datetime
import os

class PubmedScraper(Scraper):

    
