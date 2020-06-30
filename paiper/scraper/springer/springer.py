from paiper.scraper import Scraper
from progress.bar import ChargingBar
import requests
import json
import datetime
import os

SPRINGER_NATURE_API_KEY = os.environ.get('SPRINGER_NATURE_API_KEY', 'Springer key doesn\'t exist')

class SpringerScraper(Scraper):

    def _url_builder(self, s, subject, keyword):
        """
        Builds url to query Springer Nature API
        :param s: start index of returned result
        :param subject: subject constraint query
        :param keyword: keyword constraint query
        """
        # builds query
        query = 'type:Journal'
        if subject:
            query += f'+subject:\"{subject}\"'
        if keyword:
            query += f'+keyword:\"{keyword}\"'

        # builds url
        return f'http://api.springernature.com/meta/v2/json?s={s}&p=100&q=({query})&api_key={SPRINGER_NATURE_API_KEY}'

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

    def _get_creators(self, creators):
        """
        Turns list of dictionary of creators into list of creators
        :param creators: list of creators where each creator is inside a dictionary
        """
        list = []
        for creator in creators:
            list.append(creator['creator'])
        return list

    def _get_url(self, urls):
        """
        Returns generic url to paper or first url from list of urls
        :param urls: list of urls where each url is inside a dictionary
        """
        if not urls:
            return None
        for url in urls:
            if url['format'] == '':
                return url['value']
        return urls[0]['value']

    def _get_date(self, date):
        """
        Converts date into datetime object
        :param date: date formatted 'YYYY-MM-DD'
        """
        date_array = date.split('-')
        return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

    def scrape(self, subject = '', keyword = ''):
        """
        Scrapes metadata of Springer Nature articles returned by subject and
        keyword query, processes abstracts, and stores relevant articles

        :param subject: subject constraint query, if empty does not include subject
        constraint to query
        :param keyword: keyword constraint query, if empty does not include keyword
        constraint to query
        """
        stored_ids = []
        stored_abstracts = []
        new_articles = []
        new_abstracts = []
        already_stored = 0
        unreadable_papers = 0
        page = 1
        total = 100

        # prints subject and query made
        subject_print = subject if subject else 'None'
        keyword_print = keyword if keyword else 'None'
        print(f'Database: Springer Nature, Subject: {subject_print}, Keyword: {keyword_print}')

        # progress bar
        bar = ChargingBar('Getting metadata:', max = total, suffix = '%(index)d of %(max)d')

        while page <= total:
            url = self._url_builder(page, subject, keyword)
            response = requests.get(url)

            if response.ok:
                data = json.loads(response.content)
                records = data['records']

                # updates total to total number of papers in query
                if page == 1:
                    total = int(data['result'][0]['total'])
                    bar.max = total

                # gets metadata
                for record in records:
                    # checks if paper is already in database using doi
                    doi = record['doi']

                    # continue if paper already tagged by all tags
                    if self._collection.count_documents({ 'tag': { '$all': self._tags }, 'doi': doi }, limit = 1):
                        already_stored += 1
                        bar.next()
                        continue

                    # store abstract text for use by mat2vec below
                    abstract = self._get_value(record, 'abstract')

                    # continues if paper does not have abstract
                    if not abstract:
                        bar.next()
                        unreadable_papers += 1
                        continue

                    # processes abstract text using processor from mat2vec
                    try:
                        tokens, materials = self.processor.process(abstract)
                    except OverflowError:
                        bar.next()
                        unreadable_papers += 1
                        continue
                    processed_abstract = ' '.join(tokens)

                    # store id if already in collection
                    if self._collection.count_documents({ 'doi': doi }, limit = 1):
                        stored_ids.append(doi)
                        stored_abstracts.append(processed_abstract)

                    # create new document and store new article document if not in collection
                    else:
                        article = {
                            'doi': doi,
                            'title': self._get_value(record, 'title'),
                            'abstract': self._get_value(record, 'abstract'),
                            'url': self._get_url(self._get_value(record, 'url')),
                            'creators': self._get_creators(self._get_value(record, 'creators')),
                            'publication_name': self._get_value(record, 'publicationName'),
                            'issn': self._get_value(record, 'issn'),
                            'eissn': self._get_value(record, 'eIssn'),
                            'publication_date': self._get_date(self._get_value(record, 'publicationDate')),
                            'database': 'springer',
                            'processed_abstract': processed_abstract,
                            'tags': []
                        }
                        new_articles.append(article)
                        new_abstracts.append(processed_abstract)
                    bar.next()
            page += 100
        bar.finish()

        # unreadable papers
        print(f'Already stored by all tags: {already_stored}')
        print(f'Unreadable papers: {unreadable_papers}')

        self._store(stored_ids, stored_abstracts, new_articles, new_abstracts)
