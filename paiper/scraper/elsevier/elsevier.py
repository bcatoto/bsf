from paiper.scraper import Scraper
from progress.bar import ChargingBar
import requests
import json
import datetime
import os

ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY', 'Elsevier key doesn\'t exist')

class ElsevierScraper(Scraper):

    def _get_value(self, data, key):
        """
        Gets value of key from json or returns None if key doesn't exist
        :param data: dictionary to get data from
        :param key: dictionary key
        """
        try:
            return data[key]
        except KeyError:
            return None

    def _get_date(self, date):
        """
        Converts date into datetime object
        :param date: date formatted 'YYYY-MM-DD'
        """
        if not date:
            return None
        date_array = date.split('-')
        return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

    def _get_creators(self, creators):
        """
        Turns list of dictionary of creators into list of creators and ignores extraneous data
        :param creators: list of creators where each creator is inside a dictionary
        """
        if not creators:
            return None
        entries = []
        for entry in creators:
            try:
                entries.append(entry['$'])
            except TypeError:
                return entries
        return entries

    def scrape(self, query):
        """
        Scrapes metadata of Elsevier (ScienceDirect) articles returned
        by query, processes abstracts, and stores relevant articles
        :param query: Elsevier database query
        """
        print(f'Database: Science Direct, Query: {query}')

        # creates search url
        url = f'https://api.elsevier.com/content/search/sciencedirect?query={query}&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'

        # gets dois
        dois = []
        item = 0
        total = 5000

        # progress bar
        bar = ChargingBar('Getting DOIs:', max = 5000, suffix = '%(index)d of %(max)d')

        while item < total:
            response = requests.get(url)

            if response.ok:
                data = json.loads(response.content)['search-results']

                # updates total to total number of papers in query
                if item == 0:
                    total = min(5000, int(data['opensearch:totalResults']))
                    bar.max = total

                # stores dois
                for entry in data['entry']:
                    dois.append(entry['prism:doi'])
                    bar.next()

                # if current page is last page, break
                if data['link'][0]['@href'] == data['link'][3]['@href']:
                    print(item)
                    break

                # sets url to next page in search
                url = data['link'][-2]['@href']

                # json file has 25 items per page, so go to the next page
                item += 25 
        bar.finish()

        # metadata
        articles = []
        abstracts = []
        already_stored = 0
        unreadable_papers = 0

        # progress bar
        bar = ChargingBar('Getting metadata:', max = len(dois), suffix = '%(index)d of %(max)d')

        for doi in dois:
            url = f'https://api.elsevier.com/content/article/doi/{doi}?apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
            response = requests.get(url)

            if response.ok:
                try:
                    data = json.loads(response.content)['full-text-retrieval-response']['coredata']
                except json.decoder.JSONDecodeError:
                    unreadable_papers += 1
                    bar.next()
                    continue

                # checks if paper is already in database using doi
                if self._collection.count_documents({ 'doi': doi }, limit = 1):
                    already_stored += 1
                else:
                    abstract = self._get_value(data, 'dc:description')

                    # continues if paper does not have abstract
                    if not abstract:
                        unreadable_papers += 1
                        bar.next()
                        continue

                    # processes abstract text using processor from mat2vec
                    tokens, materials = self.processor.process(abstract)
                    processed_abstract = ' '.join(tokens)

                    # converts metadata to json format
                    article = {
                        'doi': doi,
                        'title': self._get_value(data, 'dc:title'),
                        'abstract': self._get_value(data, 'dc:description'),
                        'url': self._get_value(data, 'prism:url'),
                        'creators': self._get_creators(self._get_value(data, 'dc:creator')),
                        'publication_name': self._get_value(data, 'prism:publicationName'),
                        'issn': self._get_value(data, 'prism:issn'),
                        'publication_date': self._get_date(self._get_value(data, 'prism:coverDate')),
                        'database': 'ScienceDirect',
                        'processed_abstract': processed_abstract
                    }
                    articles.append(article)
                    abstracts.append(processed_abstract)
            bar.next()
        bar.finish()

        # already stored
        print(f'Already stored: {already_stored}')
        print(f'Unreadable papers: {unreadable_papers}')

        self._store(articles, abstracts)
