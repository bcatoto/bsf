from pymongo import MongoClient, UpdateOne
from progress.bar import ChargingBar
from paiper.processor import MaterialsTextProcessor
import json
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
ARTICLE_PATH = os.path.join(os.path.dirname(__file__), 'articles')

def load_articles(database_name='classifier', filename=None):
    """
    Loads all articles from all json files in articles folder into MongoDB database

    :param database_name: default to 'classifier', name of database to store data
    :param filename: gets articles from all files in articles folder if not given,
    else gets articles from given filename in articles folder
    """
    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL)[database_name]

    # gets and stores all articles from given file
    def get_file_articles(filename):
        # gets data from file
        file = open(os.path.join(ARTICLE_PATH, filename), 'r')
        data = json.load(file)
        articles = data['articles']

        # connects to collection
        name = data['name']
        collection = db[name]
        collection.create_index('id', name='id', unique=True)

        # progress bar
        print(f'Collection: {collection.database.name}.{collection.name}. File: {filename}.')
        bar = ChargingBar(f'Processing articles from \'{name}\':', max=len(articles), suffix='%(index)d of %(max)d')

        requests = []
        for article in articles:
            # processes abstracts
            tokens, materials = processor.process(article['abstract'])
            article['processed_abstract'] = ' '.join(tokens)

            # creates update request
            requests.append(UpdateOne(article, { '$setOnInsert': article }, upsert=True))
            bar.next()
        bar.finish()

        # stores new articles
        print(f'Updating collection...')
        if requests:
            mongo = collection.bulk_write(requests, ordered=False)

        print(f'Total stored in \'{name}\': {mongo.upserted_count}')
        print(f'Already stored in \'{name}\': {mongo.matched_count}')
        print()

    if filename is None:
        # gets all files in articles folder
        files = []
        for file in os.listdir(ARTICLE_PATH):
            if file.endswith('.json'):
                files.append(file)

        # store articles in all files
        for filename in files:
            get_file_articles(filename)
    else:
        # store article in given file
        get_file_articles(filename)
