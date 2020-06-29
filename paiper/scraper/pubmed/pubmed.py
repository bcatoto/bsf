from paiper.scraper import Scraper
from progress.bar import ChargingBar
from bs4 import BeautifulSoup
import requests
import json
import datetime
import re
import os

class PubmedScraper(Scraper):

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
        print(f'Database: PubMed, Term: {term}')

        # gets uids
        uids = []
        page = 0
        total = 100000

        # progress bar
        bar = ChargingBar('Getting UIDs:', max=total, suffix='%(index)d of %(max)d')

        while page < total:
            url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retstart={page}&retmax=100000'
            response = requests.get(url)

            if response.ok:
                soup = BeautifulSoup(response.content, 'html.parser')

                # updates total to total number of papers in query
                if page == 0:
                    total = int(soup.retmax.string)
                    bar.max = total

                # stores UIDs returned by query
                for id in soup.find_all('id'):
                    uids.append(id.string)
                    bar.next()

            page += 100000
        bar.finish()

        # gets metadata and abstracts
        articles = []
        abstracts = []
        already_stored = 0
        page = 0
        total = len(uids)

        # progress bar
        bar = ChargingBar('Getting metadata:', max=total, suffix='%(index)d of %(max)d')

        while page < total:
            # creates url to query metadata for 200 uids
            sub_uids = ','.join(uids[page:page + 200])
            url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={sub_uids}&retmode=xml'
            response = requests.get(url)

            if response.ok:
                soup = BeautifulSoup(response.content, 'html.parser')
                entries = soup.find_all('pubmedarticle')

                # stores UIDs returned by query
                for article in entries:

                    # checks if paper is already in database using uid or doi
                    uid = self._get_string(article.find('pmid'))
                    doi = self._get_string(article.find('elocationid', eidtype='doi'))

                    if self._collection.count_documents({ '$or': [ { 'uid': uid }, { 'doi': doi } ] }, limit = 1):
                        already_stored += 1
                    else:
                        # store abstract text for use by mat2vec below
                        abstract = self._remove_html(article.abstracttext)

                        # continues if paper does not have abstract
                        if not abstract:
                            bar.next()
                            continue

                        # processes abstract text using processor from mat2vec
                        tokens, materials = self.processor.process(abstract)
                        processed_abstract = ' '.join(tokens)

                        # converts metadata to json format
                        article = {
                            'doi': doi,
                            'uid': uid,
                            'title': self._remove_html(article.articletitle),
                            'abstract': abstract,
                            'creators': self._get_authors(article.find_all('author')),
                            'publication_name': self._remove_html(article.journal.title),
                            'issn': self._get_string(article.find('issn', issntype='Print')),
                            'eissn': self._get_string(article.find('issn', issntype='Electronic')),
                            'publication_date': self._get_date(article.articledate),
                            'database': 'pubmed',
                            'processed_abstract': processed_abstract
                        }
                        articles.append(article)
                        abstracts.append(processed_abstract)
                    bar.next()
            page += 200
        bar.finish()

        # already stored
        print(f'Already stored: {already_stored}')

        self._store(articles, abstracts)
