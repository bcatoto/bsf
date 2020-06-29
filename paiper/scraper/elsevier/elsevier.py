from paiper.scraper import Scraper
from progress.bar import ChargingBar
import requests
import json
import datetime
import os

ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY', 'Springer key doesn\'t exist')

class ElsevierScraper(Scraper):

    
