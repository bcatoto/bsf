from pymongo import MongoClient, UpdateOne
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
import spacy
import datetime
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Scraper:
    nlp = spacy.load('en_core_web_sm',  disable=['tagger', 'ner'])
    processor = MaterialsTextProcessor()

    def __init__(self, classifiers, database='abstracts', collection='all', save_all=False, gen_tag='food science'):
        """
        Initializes Scraper class

        :param classifiers: model to determine relevance of abstract
        :param database: defaults to 'abstracts', database to store abstracts in
        :param collection: defaults to 'all', collection to store abstracts in
        :param save_all: defaults to False, Bool flag to save all articles from query
        :param gen_tag: defaults to 'food science', name of tag to apply to all articles (required only if save_all is True)
        """
        self._classifiers = classifiers
        self._collection = MongoClient(DATABASE_URL)[database][collection]
        self._save = save_all
        self._gen_tag = gen_tag
        self._gen_new = 0
        self._gen_total = 0

        # create collection indices
        self._collection.create_index('doi', name='doi', unique=True, sparse=True)
        self._collection.create_index('uid', name='uid', unique=True, sparse=True)
        self._collection.create_index('pmc', name='pmc', unique=True, sparse=True)
        self._collection.create_index('tags', name='tags')
        self._collection.create_index('database', name='database')

    def _get_date(self, date):
        """
        Converts date into datetime object

        :param date: date formatted 'YYYY-MM-DD'
        """
        if not date:
            return None
        date_array = date.split('-')
        return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

    def _save_all(self, articles):
        """
        Stores all articles from database query (regardless of classifier result) under general tag

        :param articles: list of article objects to add to database
        :param doi: Bool flag for whether stored IDs are DOI
        """
        self._gen_total += len(articles)

        # creates request to store article with corresponding tag
        requests = []
        for article in articles:
            # creates document to insert by filtering out fields that are None
            doc = { k:v for k,v in article.items() if v is not None }
            doi = doc.get('doi')
            uid = doc.get('uid')
            pmc = doc.get('pmc')

            # sets either doi, uid, or pmc as the only id in that
            # preference order
            if doi:
                filter = { 'doi': doi }
                doc.pop('uid', None)
                doc.pop('pmc', None)

            elif uid:
                filter = { 'uid': uid }
                doc.pop('doi', None)
                doc.pop('pmc', None)
            else:
                filter = { 'pmc': pmc }
                doc.pop('doi', None)
                doc.pop('uid', None)

            # if article is marked as relevant, inserts new document if it
            # does not exist and adds to tag
            requests.append(UpdateOne(
                filter,
                {
                    '$setOnInsert': doc,
                    '$addToSet': { 'tags': self._gen_tag }
                },
                upsert=True
            ))

        # updates database
        if requests:
            mongo = self._collection.bulk_write(requests, ordered=False)
            self._gen_new += mongo.upserted_count + mongo.modified_count if mongo else 0

    def _store(self, articles, abstracts):
        """
        Classifies articles based on processed abstracts and stores in database
        if relevant

        :param articles: list of article objects to add to database
        :param abstracts: list of processed abstracts to be checked against classifier
        """
        for classifier in self._classifiers:
            classifier.total += len(articles)

            # uses classifier to determine if relevant
            predictions = classifier.predict(abstracts)

            # creates request to store article with corresponding tag
            requests = []
            for i, article in enumerate(articles):
                if predictions[i]:
                    # creates document to insert by filtering out fields that are None
                    doc = { k:v for k,v in article.items() if v is not None }
                    doi = doc.get('doi')
                    uid = doc.get('uid')
                    pmc = doc.get('pmc')
                    paperid = doc.get('paperid') # unique s2orc paper id

                    # sets either doi, uid, or pmc as the only id in that
                    # preference order
                    if doi:
                        filter = { 'doi': doi }
                        doc.pop('uid', None)
                        doc.pop('pmc', None)
                        doc.pop('paperid', None)
                    elif uid:
                        filter = { 'uid': uid }
                        doc.pop('doi', None)
                        doc.pop('pmc', None)
                        doc.pop('paperid', None)
                    elif pmc:
                        filter = { 'pmc': pmc }
                        doc.pop('doi', None)
                        doc.pop('uid', None)
                        doc.pop('paperid', None)
                    else:
                        filter = { 'paperid': paperid }
                        doc.pop('doi', None)
                        doc.pop('uid', None)
                        doc.pop('pmc', None)

                    # if article is marked as relevant, inserts new document if it
                    # does not exist and adds to tag
                    requests.append(UpdateOne(
                        filter,
                        {
                            '$setOnInsert': doc,
                            '$addToSet': { 'tags': classifier.tag }
                        },
                        upsert=True
                    ))

                # ignore irrelevant articles, but keep track of their number
                else:
                    classifier.irrelevant += 1

            # updates database
            if requests:
                mongo = self._collection.bulk_write(requests, ordered=False)
                classifier.relevant += mongo.upserted_count + mongo.modified_count if mongo else 0

        # if flag is marked True, store all articles from query to database
        if self._save:
            self._save_all(articles)
