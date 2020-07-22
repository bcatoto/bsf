from paiper.scraper import Scraper
import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data')

class S2ORCScraper(Scraper):
    def _get_creators(self, article):
        """
        Turns list of dictionary of creators into list of creators

        :param creators: list of creators where each creator is inside a dictionary
        """
        creators = self._get_value(article, 'authors')
        list = []
        for creator in creators:
            first = creator['first']
            middle = ' '.join(creator['middle'])
            last = creator['last']
            suffix = creator['suffix']
            list.append(f'{first} {middle} {last} {suffix}')
        return list

    def scrape(self, filename=None):
        """
        """
        print(f'Collection: {self._collection.database.name}.{self._collection.name}. Database: S2ORC.')

        abstracts = []
        articles = []
        unreadable = 0

        def get_metadata(filename):
            print(f'Getting metadata from {filename}...')

            file = open(os.path.join(DATA_PATH, filename), 'r')
            unreadable = 0

            for data in file:
                article = json.loads(data)

                # store abstract text for use by mat2vec below
                abstract = self._get_value(article, 'abstract')

                # continues if paper does not have abstract
                if not abstract:
                    unreadable += 1
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

                    processed_sent = ' '.join(tokens)
                    sentences.append(processed_sent)

                # if processor (from above) throws an error, skip the paper
                if is_unreadable:
                    unreadable += 1
                    continue

                processed_abstract = '\n'.join(sentences)

                # create new document and store new article document if not in collection
                article = {
                    'doi': self._get_value(article, 'doi'),
                    'uid': self._get_value(article, 'pubmed_id'),
                    'title': self._get_value(article, 'title'),
                    'abstract': self._get_value(article, 'abstract'),
                    'url': self._get_value(article, 's2_url'),
                    'creators': self._get_creators(article),
                    'publication_name': self._get_value(article, 'journal'),
                    'issn': None,
                    'eissn': None,
                    'publication_date': None,
                    'year': self._get_value(article, 'year'),
                    'database': 's2orc',
                    'processed_abstract': processed_abstract
                }
                articles.append(article)
                abstracts.append(processed_abstract)

            return unreadable

        if filename is None:
            # no filename specified --> gets all data in data folder
            files = []
            for file in os.listdir(DATA_PATH):
                if file.endswith('.jsonl'):
                    files.append(file)

            for filename in files:
                unreadable += get_metadata(filename)
        else:
            # store data from given file
            unreadable += get_metadata(filename)

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
