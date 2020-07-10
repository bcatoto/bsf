from pymongo import MongoClient, UpdateOne
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import spacy
import time
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:
    db = MongoClient(DATABASE_URL).abstracts
    nlp = spacy.load('en_core_web_sm')
    processor = MaterialsTextProcessor()

    def __init__(self, classifiers, collection='all', save_all=False, gen_tag='food science'):
        """
        Initializes classifiers and collection
        :param classifiers: model to determine relevance of abstract
        :param collection: defaults to 'all', collection to store abstracts in
        :param save_all: defaults to False, Bool flag to save all articles from query (rather than only those marked relevant)
        :param gen_tag: defaults to 'food science', name of tag to apply to all articles (required only if save_all is True)
        """
        self._classifiers = classifiers
        self._collection = self.db[collection]
        self._save = save_all
        self._gen_tag = gen_tag
        print(f'Collection: {collection}')

    def _get_id(self, data, key):
        """
        Gets value of id from json or returns None if id doesn't exist
        :param data: dictionary to get data from
        :param key: dictionary key
        """
        try:
            return data[key]
        except KeyError:
            return None

    def _save_all(self, articles, doi):
        """
        Stores all articles from database query (regardless of classifier result) under general tag
        :param articles: list of article objects to add to database
        :param doi: Bool flag for whether stored IDs are DOI
        """
        total = len(articles)

        # progress bar
        bar = ChargingBar(f'Storing all new papers to \'{self._gen_tag}\':', max=total, suffix='%(index)d of %(max)d')

        requests = []

        # creates request to store article with corresponding tag
        for article in articles:
            id = article['doi'] if doi else article['uid']

            # inserts new document if it does not exist
            requests.append(UpdateOne(
                { 'doi' if doi else 'uid': id, },
                {
                    '$setOnInsert': {
                        'doi': article['doi'],
                        'uid': article['uid'],
                        'title': article['title'],
                        'abstract': article['abstract'],
                        'url': article['url'],
                        'creators': article['creators'],
                        'publication_name': article['publication_name'],
                        'issn': article['issn'],
                        'eissn': article['eissn'],
                        'publication_date': article['publication_date'],
                        'database': article['database'],
                        'processed_abstract': article['processed_abstract'],
                        'tags': [self._gen_tag]
                    },
                },
                upsert=True
            ))

            # modifies existing document to include tag
            requests.append(UpdateOne(
                {
                    'doi' if doi else 'uid': id,
                    'tags': { '$ne' : self._gen_tag }
                },
                { '$push': { 'tags': self._gen_tag } }
            ))

            bar.next()
        bar.finish()

        # updates database
        print(f'Updating collection...')
        if requests:
            start = time.perf_counter()
            mongo = self._collection.bulk_write(requests, ordered=False)
            time = start - time.perf_counter()
            print(f'Bulk write operation time (unordered): {int(time / 60)}m{time % 60}s')

            start = time.perf_counter()
            mongo = self._collection.bulk_write(requests)
            time = start - time.perf_counter()
            print(f'Bulk write operation time (ordered): {int(time / 60)}m{time % 60}s')
            print()

        # calculates how many new relevant articles were added
        new = mongo.upserted_count + mongo.modified_count if mongo else 0

        print(f'Total articles analyzed: {total}.')
        print(f'Stored {new} new abstracts to \'{self._gen_tag}\'.')

    def _store(self, articles, abstracts, doi=True):
        """
        Classifies articles based on processed abstracts and stores in database
        if relevant
        :param articles: list of article objects to add to database
        :param abstracts: list of processed abstracts to be checked against classifier
        :param doi: Bool flag for whether stored IDs are DOI
        """
        # if no abstracts to store, exit
        if not abstracts:
            print('No abstracts to classify\n')
            return

        total = len(abstracts)

        for classifier in self._classifiers:
            # progress bar
            bar = ChargingBar(f'Classifying papers relevant to \'{classifier.tag}\':', max=total, suffix='%(index)d of %(max)d')

            # uses classifier to determine if relevant
            predictions = classifier.predict(abstracts)

            requests = []
            irrelevant = 0

            # creates request to store article with corresponding tag
            for i, article in enumerate(articles):
                id = article['doi'] if doi else article['uid']

                # if article is marked as relevant, store metadata
                if predictions[i]:
                    # inserts new document if it does not exist
                    requests.append(UpdateOne(
                        { 'doi' if doi else 'uid': id, },
                        {
                            '$setOnInsert': {
                                'doi': article['doi'],
                                'uid': article['uid'],
                                'title': article['title'],
                                'abstract': article['abstract'],
                                'url': article['url'],
                                'creators': article['creators'],
                                'publication_name': article['publication_name'],
                                'issn': article['issn'],
                                'eissn': article['eissn'],
                                'publication_date': article['publication_date'],
                                'database': article['database'],
                                'processed_abstract': article['processed_abstract'],
                                'tags': [ classifier.tag ]
                            },
                        },
                        upsert=True
                    ))

                    # modifies existing document to include tag
                    requests.append(UpdateOne(
                        {
                            'doi' if doi else 'uid': id,
                            'tags': { '$ne' : classifier.tag }
                        },
                        { '$push': { 'tags': classifier.tag } }
                    ))
                # ignore irrelevant articles, but keep track of their number
                else:
                    irrelevant += 1
                bar.next()
            bar.finish()

            # updates database
            print(f'Updating collection...')
            if requests:
                start = time.perf_counter()
                mongo = self._collection.bulk_write(requests, ordered=False)
                elapsed = start - time.perf_counter()
                print(f'Bulk write operation time (unordered): {int(elapsed / 60)}m{elapsed % 60:0.2f}s')

                start = time.perf_counter()
                mongo = self._collection.bulk_write(requests)
                elapsed = start - time.perf_counter()
                print(f'Bulk write operation time (ordered): {int(elapsed / 60)}m{elapsed % 60:0.2f}s')
                print()

            # calculates how many new relevant articles were added
            relevant = mongo.upserted_count + mongo.modified_count if mongo else 0

            print(f'Total articles analyzed: {total}.')
            print(f'Stored {relevant} new abstracts relevant to \'{classifier.tag}\'.')
            print(f'Ignored {irrelevant} abstracts irrelevant to \'{classifier.tag}\'.')
            print(f'Ignored {total - relevant - irrelevant} articles already tagged as \'{classifier.tag}\'.')
            print()

        # if flag is marked True, store all articles from query to database (ignore classification filter)
        if self._save:
            self._save_all(articles, doi)

    def set_classifiers(self, classifiers):
        """
        Sets classifier
        :param classifiers: model to determine relevance of abstract
        """
        self._classifiers = classifiers

    def set_collection(self, collection):
        """
        Sets collection
        :param collection: collection to store abstracts and metadata in
        """
        self._collection = db[collection]
        print(f'Collection: {collection}')
