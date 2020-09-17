from shearlock.scraper import Scraper
from progress.counter import Counter
import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')

class S2ORCScraper(Scraper):
    def _get_creators(self, creators):
        """
        Turns list of dictionary of creators into list of creators

        :param creators: dictionary from article['authors']
        """
        list = []
        for creator in creators:
            first = creator['first']
            middle = ' '.join(creator['middle'])
            last = creator['last']
            suffix = creator['suffix']
            list.append(f'{first} {middle} {last} {suffix}')
        return list

    def scrape(self, filename):
        """
        Scrapes metadata of S2ORC articles from given file

        :param filename: name of file in data folder to scrape from
        """
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: S2ORC. File: {filename}')

        abstracts = []
        articles = []
        no_id = 0
        unreadable = 0

        # counter
        counter = Counter(message='Articles analyzed: ')

        file = open(os.path.join(DATA_PATH, filename), 'r')

        # load GB to US dictionary
        with open('miscellaneous/us_gb_dict.txt', 'r') as convert:
            spelling = json.load(convert)
        print('Stored json dictionary in memory')

        for data in file:
            article = json.loads(data)

            # ignore abstract if article is not from PubMed or PubMedCentral
            uid = article.get('pubmed_id')
            pmc = article.get('pmc_id')
            doi = article.get('doi')
            paperid = article.get('paper_id')
            if not uid and not pmc and not doi and not paperid:
                no_id += 1
                counter.next()
                continue

            # store abstract text for use by mat2vec below
            abstract = article.get('abstract')

            # continues if paper does not have abstract
            if not abstract:
                unreadable += 1
                counter.next()
                continue

            # replaces ':::' with newline
            abstract = abstract.replace('::: ', '\n')

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
                
                processed_sent = ' '.join([token.lemma_ for token in sent if not token.is_stop])
                for gb, us in spelling.items():
                    processed_sent = processed_sent.replace(gb, us)
                sentences.append(processed_sent)

            # if processor (from above) throws an error, skip the paper
            if is_unreadable:
                unreadable += 1
                counter.next()
                continue

            processed_abstract = '\n'.join(sentences)

            # create new document and store new article document if not in collection
            article = {
                'doi': doi,
                'uid': uid,
                'pmc': pmc,
                'paperid': paperid,
                'title': article.get('title'),
                'abstract': abstract,
                'url': article.get('s2_url'),
                'creators': self._get_creators(article.get('authors')),
                'publication_name': article.get('journal'),
                'year': article.get('year'),
                'database': 's2orc',
                'processed_abstract': processed_abstract
            }
            articles.append(article)
            abstracts.append(processed_abstract)
            counter.next()

            # classify abstracts if 20000 have been stored
            if len(abstracts) == 20000:
                self._store(articles, abstracts)
                articles = []
                abstracts = []
        counter.finish()

        # unreadable papers
        print(f'No ID: {no_id}')
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
