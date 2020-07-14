from pymongo import MongoClient, UpdateOne
from progress.bar import ChargingBar
from paiper.processor import MaterialsTextProcessor
import json
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
ARTICLE_PATH = os.path.join(os.path.dirname(__file__), 'articles')

def load_articles(filename, collection_name):
    """
    Loads all articles from all json files in articles folder into MongoDB database
    """
    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).classifier

    # gets all files in articles folder
    files = []
    for file in os.listdir(ARTICLE_PATH):
        if file.endswith('.json'):
            files.append(file)

    already_stored = 0

    for i, filename in enumerate(files):
        # gets data from file
        file = open(os.path.join(ARTICLE_PATH, filename), 'r')
        data = json.load(file)
        articles = data['articles']

        # connects to collection
        name = data['from']
        collection = db[name]
        collection.create_index(('id', 1), name='id', unique=True)

        # progress bar
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
