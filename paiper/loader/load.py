# loads the training data (annotated abstracts) into MongoDB

from pymongo import MongoClient
from paiper.processor import MaterialsTextProcessor
from sys import argv, stderr
import json
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
ARTICLE_PATH = os.path.join(os.path.dirname(__file__), 'articles')

def load_data():
    """
    Loads all articles from all json files in articles folder into MongoDB
    database
    """
    processor = MaterialsTextProcessor()
    db = MongoClient(DATABASE_URL).training

    # gets all files in articles folder
    files = []
    for file in os.listdir(ARTICLE_PATH):
        if file.endswith('.json'):
            files.append(file)

    for i, filename in enumerate(files):
        print(f'Reading file {i + 1}/{len(files)}...')

        # gets data from file
        file = open(os.path.join(ARTICLE_PATH, filename), 'r')
        data = json.load(file)
        articles = data['articles']

        # connects to proper collectin
        coll = db[data['from']]

        for j, article in enumerate(articles):
            print(f'\tStoring article {j + 1}/{len(articles)}...')

            doi = article['doi']
            if coll.count_documents({ 'doi': doi }, limit = 1):
                print(f'\tThis paper is already stored: {doi}')
            else:
                tokens, materials = processor.process(article['abstract'])
                article['processed_abstract'] = ' '.join(tokens)
                coll.insert_one(article)

    print('Operation completed')