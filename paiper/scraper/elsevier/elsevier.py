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
    
    def scrape_faster(self, query):
        """
        Note: requires institutional access by VPN, or else an error will be thrown
        Faster implementation of scrape()

        Scrapes metadata of Elsevier (ScienceDirect) articles returned
        by query, processes abstracts, and stores relevant articles

        :param query: Elsevier database query
        """
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: Elsevier. Query: {query}.')
        
        # create url
        url = f'https://api.elsevier.com/content/metadata/article?query=KEY({query})&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'

        articles = []
        abstracts = []
        no_doi = 0
        unreadable = 0
        item = 0
        total = 5000
        
        # progress bar
        bar = ChargingBar('Getting metadata:', max = total, suffix = '%(index)d of %(max)d - %(elapsed_td)s')
        
        while item < total:
            response = requests.get(url)

            if response.ok:
                data = json.loads(response.content)['search-results']
                records = data['entry']

                # updates total to total number of papers in query
                if item == 0:
                    total = min(5000, int(data['opensearch:totalResults']))
                    bar.max = total

                    # if there are no results, exit
                    if total == 0:
                        print('Search returned no results.\n')
                        return
                
                for record in records:
                    doi = record.get('prism:doi')
                    if not doi:
                        no_doi += 1
                        bar.next()
                        continue

                    abstract = record.get('prism:teaser')

                    # if there is no abstract, skip this article
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
                        'doi': doi,
                        'uid': None,
                        'title': record.get('dc:title'),
                        'abstract': abstract,
                        'url': record.get('prism:url'),
                        'creators': self._get_creators(data.get('dc:creator')),
                        'publication_name': data.get('prism:publicationName'),
                        'issn': record.get('prism:issn'),
                        'publication_date': self._get_date(data.get('prism:coverDate')),
                        'database': 'elsevier',
                        'processed_abstract': processed_abstract
                    }
                    articles.append(article)
                    abstracts.append(processed_abstract)
                    bar.next()
            
                # sets url to next page in search
                url = data['link'][-2]['@href']
            
            # json file has 25 items per page, so go to the next page
            item += 25
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
        bar = ChargingBar('Getting DOIs:', max = total, suffix = '%(index)d of %(max)d - %(elapsed_td)s')

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
                    doi = entry.get('prism:doi')
                    if doi:
                        dois.append(current_doi)
                    bar.next()

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
        bar = ChargingBar('Getting metadata:', max = len(dois), suffix = '%(index)d of %(max)d - %(elapsed_td)s')

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
                abstract = data.get('dc:description')

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
                    'title': data.get('dc:title'),
                    'abstract': abstract,
                    'url': data.get('prism:url'),
                    'creators': self._get_creators(data.get('dc:creator')),
                    'publication_name': data.get('prism:publicationName'),
                    'issn': data.get('prism:issn'),
                    'publication_date': self._get_date(data.get('prism:coverDate')),
                    'database': 'elsevier',
                    'processed_abstract': processed_abstract,
                }
                articles.append(article)
                abstracts.append(processed_abstract)
            bar.next()
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
