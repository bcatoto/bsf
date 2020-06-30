from pymongo import MongoClient
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:

    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).abstracts

    def __init__(self, collection = 'default', classifier = None):
        self._collection = self.db[collection]
        self._classifier = classifier

    def _store(self, articles, abstracts):
        """
        Classifies articles based on processed abstracts and stores in database
        if relevant

        :param articles: list of metadata of abstracts
        :param abstracts: list of processed abstracts to predict on
        """
        # if no abstracts to store, exit
        if not abstracts:
            print('No abstracts to store')
            return

        # uses classifier to determine if relevant
        predictions = self._classifier.predict(abstracts)

        # keeps articles to be stored in database
        relevant = []

        # progress bar
        bar = ChargingBar('Classifying papers:', max = len(abstracts), suffix = '%(index)d of %(max)d')

        # appends articles to be stored in database to relevant list if relevant
        for i, article in enumerate(articles):
            if predictions[i]:
                relevant.append(article)
            bar.next()
        bar.finish()

        # stores relevant abstracts in database
        if relevant:
            self._collection.insert_many(relevant)

        print(f'Successfully stored {len(relevant)} papers to database.')
        print(f'Relevant abstracts: {len(relevant)}')
        print(f'Irrelevant abstracts: {len(articles) - len(relevant)}')
        print(f'Total: {len(articles)}')

    def set_collection(self, collection):
        self._collection = db[collection]

    def set_classifier(self, classifier):
        self._classifier = classifier
