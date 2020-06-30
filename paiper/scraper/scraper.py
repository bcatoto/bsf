from pymongo import MongoClient
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:

    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).abstracts

    def __init__(self, tag, classifier, collection = 'all'):
        self._tag = tag
        self._classifier = classifier
        self._collection = self.db[collection]

    def _store(self, stored_ids, stored_abstracts, new_articles, new_abstracts, uid=False):
        """
        Classifies articles based on processed abstracts and stores in database
        if relevant
        :param stored_ids: ids of already stored documents
        :param stored_abstracts: list of processed stored abstracts to predict on
        :param new_articles: list of metadata of new abstracts
        :param new_abstracts: list of new processed abstracts to predict on
        :param uid: Bool flag for whether stored IDs are UIDs
        """
        # if no abstracts to store, exit
        if not stored_abstracts and not new_abstracts:
            print('No abstracts to store')
            return

        relevant_count = 0

        # updates already stored abstracts with new tag
        if stored_abstracts:
            # uses classifier to determine if relevant
            predictions = self._classifier.predict(stored_abstracts)

            # keeps articles to be stored in database
            relevant = []

            # progress bar
            bar = ChargingBar('Classifying papers:', max = len(stored_abstracts), suffix = '%(index)d of %(max)d')

            # appends articles to be stored in database to relevant list if relevant
            for i, id in enumerate(stored_ids):
                if predictions[i]:
                    relevant.append(id)
                    relevant_count += 1
                bar.next()
            bar.finish()

            # if relevant articles exist, store in database
            if relevant:
                self._collection.update_many({ 'uid' if uid else 'doi': { '$in': relevant } }, { '$push': { 'tag': self._tag } })

        if new_abstracts:
            # uses classifier to determine if relevant
            predictions = self._classifier.predict(new_abstracts)

            # keeps articles to be stored in database
            relevant = []

            # progress bar
            bar = ChargingBar('Classifying papers:', max = len(stored_abstracts), suffix = '%(index)d of %(max)d')

            # appends articles to be stored in database to relevant list if relevant
            for i, article in enumerate(new_articles):
                if predictions[i]:
                    relevant.append(article)
                    relevant_count += 0
                bar.next()
            bar.finish()

            # if relevant articles exist, store in database
            if relevant:
                self._collection.insert_many(relevant)

        print(f'Relevant abstracts: {relevant_count}')
        print(f'Irrelevant abstracts: {len(stored_abstracts) + len(new_abstracts) - relevant_count}')
        print(f'Total: {len(stored_abstracts) + len(new_abstracts)}')

    def set_tag(self, tag):
        self._tag = tag

    def set_collection(self, collection):
        self._collection = db[collection]

    def set_classifier(self, classifier):
        self._classifier = classifier
