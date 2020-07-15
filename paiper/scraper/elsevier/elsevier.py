from paiper.scraper import Scraper
from progress.bar import ChargingBar
import requests
import json
import os

ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY', 'Elsevier key doesn\'t exist')

class ElsevierScraper(Scraper):

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
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: Elsevier. Query: {query}.')

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
                    try:
                        dois.append(entry['prism:doi'])
                    except KeyError:
                        bar.next()
                        continue
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
        unreadable = 0

        if not dois:
            print('No abstracts to classify.\n')
            return

        # progress bar
        bar = ChargingBar('Getting metadata:', max = len(dois), suffix = '%(index)d of %(max)d')

        for doi in dois:
            url = f'https://api.elsevier.com/content/article/doi/{doi}?apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
            response = requests.get(url)

            if response.ok:
                try:
                    data = json.loads(response.content)['full-text-retrieval-response']['coredata']
                except json.decoder.JSONDecodeError:
                    unreadable += 1
                    bar.next()
                    continue

                # store abstract text for use by mat2vec below
                abstract = self._get_value(data, 'dc:description')

                # continues if paper does not have abstract
                if not abstract:
                    unreadable += 1
                    bar.next()
                    continue

                # segments abstract by sentence
                doc = self.nlp(abstract)
                sentences = []
                is_unreadable = False

                # processes sentence text using processor from mat2vec
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
                    bar.next()
                    unreadable += 1
                    continue

                processed_abstract = '\n'.join(sentences)

                article = {
                    'doi': doi,
                    'uid': None,
                    'title': self._get_value(data, 'dc:title'),
                    'abstract': self._get_value(data, 'dc:description'),
                    'url': self._get_value(data, 'prism:url'),
                    'creators': self._get_creators(self._get_value(data, 'dc:creator')),
                    'publication_name': self._get_value(data, 'prism:publicationName'),
                    'issn': self._get_value(data, 'prism:issn'),
                    'eissn': None,
                    'publication_date': self._get_date(self._get_value(data, 'prism:coverDate')),
                    'database': 'elsevier',
                    'processed_abstract': processed_abstract,
                }
                articles.append(article)
                abstracts.append(processed_abstract)
            bar.next()

            # classify abstracts if 20000 have been stored
            # note: this condition will never be met due to article scraping limit set above
            if len(abstracts) == 20000:
                self._store(articles, abstracts)
                articles = []
                abstracts = []
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
            print(f'Total articles analyzed: {self._gen_total}.')
            print(f'Stored {self._gen_new} new abstracts to \'{self._gen_tag}\'.')
            print()
            self._gen_new = 0
            self._gen_total = 0
