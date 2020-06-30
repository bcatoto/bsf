from pymongo import MongoClient
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:

    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).abstracts

    def __init__(self, tags, classifiers, collection = 'all'):
        """
        Initializes tags, classifiers, and collection
        :param tags: tags associated with each classifier to properly label
        which classifier(s) a document is relevant to
        :param classifiers: model to determine relevance of abstract
        :param collection: defaults to 'all', collection to store abstracts in
        """
        self._tags = tags
        self._classifiers = classifiers
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
            print('No abstracts to classify')
            return

        # counts
        relevant_count = [0] * len(self._classifiers)
        already_stored = [0] * len(self._classifiers)
        total = len(stored_abstracts) + len(new_abstracts)

        # progress bar
        max = len(self._classifiers) * total
        bar = ChargingBar('Classifying papers:', max=max, suffix='%(index)d of %(max)d')

        for i, classifier in enumerate(self._classifiers):
            # classifies articles already stored in collection
            if stored_abstracts:
                # uses classifier to determine if relevant
                predictions = classifier.predict(stored_abstracts)

                # ids (doi or uid) of relevant articles
                ids = []

                # appends id if article is relevant
                for j, id in enumerate(stored_ids):
                    # if article already tagged, continue
                    if self._collection.count_documents({ 'tags': self._tags[i], 'uid' if uid else 'doi': id }, limit = 1):
                        bar.next()
                        already_stored[i] += 1
                        continue

                    if predictions[j]:
                        ids.append(id)
                        relevant_count[i] += 1
                    bar.next()

                # if relevant articles exist, update tags in database
                if ids:
                    self._collection.update_many({ 'uid' if uid else 'doi': { '$in': ids }, 'tags': { '$ne' : self._tags[i] } }, { '$push': { 'tags': self._tags[i] } })

            # classifies new articles not stored in colletion
            if new_abstracts:
                # uses classifier to determine if relevant
                predictions = classifier.predict(new_abstracts)

                # appends corresponding tag if article is relevant
                for j, article in enumerate(new_articles):
                    if predictions[j]:
                        article['tags'].append(self._tags[i])
                        relevant_count[i] += 1
                    bar.next()
        bar.finish()

        # stores relevant articles based on if tags field contains tags
        relevant = []
        for article in new_articles:
            if article['tags']:
                relevant.append(article)
        if relevant:
            self._collection.insert_many(relevant)

        # prints relevant, irrelevant, and already tagged articles for each tag
        print(f'Total: {total}')
        for i, tag in enumerate(self._tags):
            print()
            print(f'Abstracts relevant to \'{tag}\': {relevant_count[i]}')
            print(f'Abstracts irrelevant to \'{tag}\': {total - relevant_count[i] - already_stored[i]}')
            print(f'Already tagged by \'{tag}\': {already_stored[i]}')

    def set_tags(self, tags):
        """
        Sets tag
        :param tags: tags associated with each classifier to properly label
        which classifier(s) a document is relevant to
        """
        self._tags = tags

    def set_classifiers(self, classifiers):
        """
        Sets classifier
        :param classifiers: model to determine relevance of abstract
        """
        self._classifiers = classifiers

    def set_collection(self, collection):
        """
        Sets collection
        :param collection: collection to store abstracts and metadata in in
        """
        self._collection = db[collection]
