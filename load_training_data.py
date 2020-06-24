# loads the training data (annotated abstracts) into MongoDB

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
    or irrelevant (all lowercase). Files are titled name_relevant or name_irrelevant
    """

    # validate command-line arguments
    if len(argv) < 3:
        print('Name or relevance missing', file=stderr)

    path = 'articles/%s_%s.json' % (argv[1], argv[2])
    COLL = DB[argv[1]]

    relevance = ('relevant' == argv[2]) # store True or False

    with open(path) as file:
        data = json.load(file)

        # check if json file has already been inserted into MongoDB by comparing article counts
        # assumption: the json file hasn't been changed (original set of articles)
        if COLL.count_documents({'relevant': relevance}) == len(data['articles']):
            print('Articles already in collection. Exiting...')
        
        else: 
            for article in data['articles']:
                tokens, materials = PROCESSOR.process(article['abstract'])
                article['processed_abstract'] = ' '.join(tokens)
            
            COLL.insert_many(data['articles'])
            print('Operation completed')

if __name__ == '__main__':
    main()
