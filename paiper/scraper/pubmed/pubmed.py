from paiper.scraper import Scraper
from progress.bar import ChargingBar
from bs4 import BeautifulSoup
import requests
import json
import datetime
import re
import os

PUBMED_API_KEY = os.environ.get('PUBMED_API_KEY', 'PubMed key doesn\'t exist')

class PubmedScraper(Scraper):
    """
    Note: the PubMed API has the tendency to return the same doi multiple times for a query.
    As a result, the number of new articles stored may be much less than anticipated (articles that
    were previously inserted are correctly ignored in _store() in the Scraper class)
    """

    def _remove_html(self, element):
        """
        Removes HTML formatting from contents of field

        :param element: HTML/XML element of field
        """
        if not element:
            return None
        string = ''
        for content in element.contents:
            string += re.sub('\s*\<[^)]*\>', '', str(content))
        return string

    def _get_authors(self, authors):
        """
        Turns XML element of authors into list of authors

        :param authors: XML element containing authors
        """
        list = []
        for author in authors:
            last_name = author.lastname.string if author.lastname else ''
            fore_name = author.forename.string if author.forename else ''
            list.append(f'{last_name}, {fore_name}')
        return list

    def _get_date(self, date):
        """
        Converts XML date element into datetime object

        :param date: date element containing year, month, and date elements
        """
        if not date:
            return None
        return datetime.datetime(int(date.year.string), int(date.month.string), int(date.day.string))

    def _get_string(self, element):
        """
        Returns string of XML element if element exists

        :param element: XML element
        """
        return element.string if element else None

    def scrape(self, term):
        """
        Scrapes metadata of PubMed articles returned by search term query, processes
        abstracts, and stores relevant articles

        :param term: PubMed term query
        """
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: PubMed. Term: {term}.')

        base = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
        retmax = 10000
        unreadable = 0
        abstracts = []
        articles = []
        page = 0
        total = retmax

        # progress bar
        bar = ChargingBar('Getting metadata:', max=total, suffix='%(index)d of %(max)d - %(elapsed_td)s')

        while page < total:
            # gets and stores to history UIDs of query
            url = f'{base}/esearch.fcgi?db=pubmed&term={term}&retstart={page}'
            url += f'&retmax={retmax}&usehistory=y&api_key={PUBMED_API_KEY}'
            response = requests.get(url)

            if not response.ok:
                print(f'\nPubmedScraper could not get UIDs for \'{term}\' on page {page}.')
                continue

            # gets info for retrieving UIDs from history
            soup = BeautifulSoup(response.content, 'html.parser')
            web = soup.webenv.string
            key = soup.querykey.string
            total = int(soup.count.string)
            bar.max = total

            # gets metadata for articles from UIDs
            url = f'{base}/efetch.fcgi?db=pubmed&WebEnv={web}'
            url += f'&query_key={key}&retstart={page}&retmax={retmax}'
            url += f'&retmode=xml&api_key={PUBMED_API_KEY}'
            response = requests.get(url)

            if not response.ok:
                print(f'\nPubmedScraper could not get metadata for \'{term}\' on page {page}.')
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            entries = soup.find_all('pubmedarticle')

            for article in entries:
                # store abstract text for use by mat2vec below
                abstract = self._remove_html(article.abstracttext)

                # continues if paper does not have abstract
                if not abstract:
                    unreadable += 1
                    bar.next()
                    continue

                # segments abstract by sentence
                doc = self.nlp(abstract)
                sentences = []
                is_unreadable = False

                for sent in doc.sents:
                    # processes sentence text using processor from mat2vec
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
                    'doi': self._get_string(article.find('elocationid', eidtype='doi')),
                    'uid': self._get_string(article.find('pmid')),
                    'title': self._remove_html(article.articletitle),
                    'abstract': abstract,
                    'url': None,
                    'creators': self._get_authors(article.find_all('author')),
                    'publication_name': self._remove_html(article.journal.title),
                    'issn': self._get_string(article.find('issn', issntype='Print')),
                    'eissn': self._get_string(article.find('issn', issntype='Electronic')),
                    'publication_date': self._get_date(article.articledate),
                    'database': 'pubmed',
                    'processed_abstract': processed_abstract,
                }
                articles.append(article)
                abstracts.append(processed_abstract)
                bar.next()

                # classify abstracts if 20000 have been stored
                if len(abstracts) == 20000:
                    self._store(articles, abstracts)
                    articles = []
                    abstracts = []
            page += retmax
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
