from pymongo import MongoClient, UpdateOne
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
import spacy
import time
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:
    db = MongoClient(DATABASE_URL).abstracts
    nlp = spacy.load('en_core_web_sm')
    processor = MaterialsTextProcessor()

    def __init__(self, classifiers, collection, save_all=False, gen_tag='food science'):
        """
        Initializes classifiers and collection
        :param classifiers: model to determine relevance of abstract
        :param collection: collection to store abstracts in
        :param save_all: defaults to False, Bool flag to save all articles from query (rather than only those marked relevant)
        :param gen_tag: defaults to 'food science', name of tag to apply to all articles (required only if save_all is True)
        """
        self._classifiers = classifiers
        self._collection = self.db[collection]
        self._save = save_all
        self._gen_tag = gen_tag
        self._gen_new = 0

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

        # creates request to store article with corresponding tag
        requests = []
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
                        'processed_abstract': article['processed_abstract']
                    },
                    '$addToSet': { 'tags': self._gen_tag }
                },
                upsert=True
            ))

        # updates database
        if requests:
            start = time.perf_counter()
            mongo = self._collection.bulk_write(requests, ordered=False)
            elapsed = start - time.perf_counter()
            print(f'Bulk write operation time: {int(elapsed / 60)}m{elapsed % 60:0.2f}s')
            self._gen_new += mongo.upserted_count + mongo.modified_count if mongo else 0

    def _store(self, articles, abstracts, doi=True):
        """
        Classifies articles based on processed abstracts and stores in database
        if relevant
        :param articles: list of article objects to add to database
        :param abstracts: list of processed abstracts to be checked against classifier
        :param doi: Bool flag for whether stored IDs are DOI
        """
        total = len(abstracts)

        for classifier in self._classifiers:
            classifier.total += total

            # uses classifier to determine if relevant
            predictions = classifier.predict(abstracts)

            # creates request to store article with corresponding tag
            requests = []
            for i, article in enumerate(articles):
                id = article['doi'] if doi else article['uid']

                # if article is marked as relevant, inserts new document if it
                # does not exist and adds to tag
                if predictions[i]:
                    requests.append(UpdateOne(
                        { 'doi' if doi else 'uid': id },
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
                                'processed_abstract': article['processed_abstract']
                            },
                            '$addToSet': { 'tags': classifier.tag }
                        },
                        upsert=True
                    ))

                # ignore irrelevant articles, but keep track of their number
                else:
                    classifier.irrelevant += 1

            # updates database
            if requests:
                start = time.perf_counter()
                mongo = self._collection.bulk_write(requests, ordered=False)
                elapsed = start - time.perf_counter()
                print(f'Bulk write operation time: {int(elapsed / 60)}m{elapsed % 60:0.2f}s')
                classifier.relevant += mongo.upserted_count + mongo.modified_count if mongo else 0

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
