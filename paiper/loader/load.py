from pymongo import MongoClient
from progress.bar import ChargingBar
from paiper.processor import MaterialsTextProcessor
from sys import argv, stderr
import json
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
ARTICLE_PATH = os.path.join(os.path.dirname(__file__), 'articles')

def load_articles():
    """
    Loads all articles from all json files in articles folder into MongoDB
    database
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

        # connects to proper collection
        name = data['from']
        coll = db[name]
        coll.create_index("id", unique=True)

        new = []

        # progress bar
        bar = ChargingBar(f'Storing articles from \'{name}\':', max=len(articles), suffix='%(index)d of %(max)d')

        for j, article in enumerate(articles):
            # checks if article is already in database and only stores new
            # articles
            if coll.count_documents({ 'id': article['id'] }, limit = 1):
                already_stored += 1
            else:
                tokens, materials = processor.process(article['abstract'])
                article['processed_abstract'] = ' '.join(tokens)
                new.append(article)
            bar.next()
        bar.finish()

        # stores new articles
        if new:
            coll.insert_many(new)

        print(f'Total stored in \'{name}\': {len(new)}')
        print(f'Already stored in \'{name}\': {already_stored}')
