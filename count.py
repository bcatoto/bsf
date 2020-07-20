from pymongo import MongoClient
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

def main():
    tags = ['gabby', 'matthew', 'food science']

    collection = MongoClient(DATABASE_URL).abstracts.all

    for tag in tags:
        count = collection.count_documents({ 'tags': tag })
        print(f'{tag}: {count}')

if __name__ == '__main__':
    main()
