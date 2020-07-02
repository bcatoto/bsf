from pymongo import MongoClient, UpdateOne
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:
    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).abstracts

    def __init__(self, classifiers, collection = 'all'):
        """
        Initializes classifiers and collection
        :param classifiers: model to determine relevance of abstract
        :param collection: defaults to 'all', collection to store abstracts in
        """
        self._classifiers = classifiers
        self._collection = self.db[collection]
        print(f'Collection: {collection}')

    def _get_id(self, data, key):
        try:
            return data[key]
        except KeyError:
            return None

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
            print('No abstracts to classify')
            return

        total = len(abstracts)

        for classifier in self._classifiers:
            # progress bar
            bar = ChargingBar(f'Classifying papers relevant to \'{classifier.tag}\':', max=total, suffix='%(index)d of %(max)d')

            # uses classifier to determine if relevant
            predictions = classifier.predict(abstracts)

            requests = []
            irrelevant = 0

            # creates request to stor article with corresponding tag
            for i, article in enumerate(articles):
                id = article['doi'] if doi else article['uid']

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
                else:
                    irrelevant += 1
                bar.next()
            bar.finish()

            # updates database
            print(f'Updating collection...')
            if requests:
                mongo = self._collection.bulk_write(requests)

            # calculates how many new relevant articles were added
            relevant = mongo.upserted_count + mongo.modified_count if mongo else 0

            print(f'Total articles analyzed: {total}.')
            print(f'Stored {relevant} new abstracts relevant to \'{classifier.tag}\'.')
            print(f'Ignored {irrelevant} abstracts irrelevant to \'{classifier.tag}\'.')
            print(f'Ignored {total - relevant - irrelevant} articles already tagged as \'{classifier.tag}\'.')
            print()

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
        print(f'Collection: {collection}')
