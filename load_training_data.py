from pymongo import MongoClient
from process import MaterialsTextProcessor
from sys import argv, stderr
import json
import os

PROCESSOR = MaterialsTextProcessor()

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
DB = MongoClient(DATABASE_URL).training

def main():
    """
    Loads data from json file in articles folder into MongoDB database
    Command-line arguments should be name and whether the articles are relevant
    or irrelevant (all lowercase)
    """
    if len(argv) < 3:
        print('Name or relevance missing', file=stderr)

    path = 'articles/%s_%s.json' % (argv[1], argv[2])
    coll = DB[argv[1]]

    with open(path) as file:
        data = json.load(file)

        for article in data['articles']:
            tokens, materials = PROCESSOR.process(article['abstract'])
            article['processed_abstract'] = ' '.join(tokens)

        coll.insert_many(data['articles'])

if __name__ == '__main__':
    main()
