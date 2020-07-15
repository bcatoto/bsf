from paiper.scraper import Scraper
from progress.bar import ChargingBar
import requests
import json
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

    def scrape(self, subject = '', keyword = ''):
        """
        Scrapes metadata of Springer Nature articles returned by subject and
        keyword query, processes abstracts, and stores relevant articles

        :param subject: subject constraint query, if empty does not include subject
        constraint to query
        :param keyword: keyword constraint query, if empty does not include keyword
        constraint to query
        """
        # prints subject and query made
        subject_print = subject if subject else 'None'
        keyword_print = keyword if keyword else 'None'
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: Springer Nature. Subject: {subject_print}, Keyword: {keyword_print}.')

        articles = []
        abstracts = []
        unreadable = 0
        item = 0
        total = 100

        # progress bar
        bar = ChargingBar('Getting metadata:', max = total, suffix = '%(index)d of %(max)d')

        while item < total:
            # builds url and queries API
            url = self._url_builder(item, subject, keyword)
            response = requests.get(url)

            if response.ok:
                data = json.loads(response.content)
                records = data['records']

                # updates total to total number of papers in query
                if item == 0:
                    total = int(data['result'][0]['total'])
                    bar.max = total

                # gets metadata
                for record in records:
                    # store abstract text for use by mat2vec below
                    abstract = self._get_value(record, 'abstract')

                    # continues if paper does not have abstract
                    if not abstract:
                        unreadable += 1
                        bar.next()
                        continue

                    # segments abstract by sentence
                    doc = self.nlp(abstract)
                    sentences = []
                    is_unreadable = False

                    # processes sentence text using mat2vec processor
                    for sent in doc.sents:
                        try:
                            tokens, materials = self.processor.process(sent.text)
                        except OverflowError:
                            is_unreadable = True
                            break

                        processed_sent = ' '.join(tokens)
                        sentences.append(processed_sent)

                    # if processor (from above) throws an error, skip the paper
                    if is_unreadable:
                        unreadable += 1
                        bar.next()
                        continue

                    processed_abstract = '\n'.join(sentences)

                    # create new document and store new article document if not in collection
                    article = {
                        'doi': self._get_value(record, 'doi'),
                        'uid': None,
                        'title': self._get_value(record, 'title'),
                        'abstract': self._get_value(record, 'abstract'),
                        'url': self._get_url(self._get_value(record, 'url')),
                        'creators': self._get_creators(self._get_value(record, 'creators')),
                        'publication_name': self._get_value(record, 'publicationName'),
                        'issn': self._get_value(record, 'issn'),
                        'eissn': self._get_value(record, 'eIssn'),
                        'publication_date': self._get_date(self._get_value(record, 'publicationDate')),
                        'database': 'springer',
                        'processed_abstract': processed_abstract
                    }
                    articles.append(article)
                    abstracts.append(processed_abstract)
                    bar.next()

                    # classify abstracts if 20000 have been stored
                    if len(abstracts) == 20000:
                        self._store(articles, abstracts)
                        articles = []
                        abstracts = []

            # 100 items per page, so go to next page
            item += 100
        bar.finish()

        # unreadable papers
        print(f'Unreadable papers: {unreadable}')

        # classifies and stores metadata
        if abstracts:
            self._store(articles, abstracts)
            print()
        else:
            print('No abstracts to classify.\n')
            return

        # prints classifier metrics
        for classifier in self._classifiers:
            classifier.print_metrics()
            classifier.reset_metrics()

        # prints general tag metrics
        if self._save:
            print(f'Total articles analyzed: {total - unreadable}.')
            print(f'Stored {self._gen_new} new abstracts to \'{self._gen_tag}\'.')
            print()
            self._gen_new = 0
