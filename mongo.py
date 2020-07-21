from pymongo import MongoClient, UpdateMany
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

def main():
    collection = MongoClient(DATABASE_URL).abstracts.all

    print('Making requests...')
    requests = []
    requests.append(UpdateMany(
        { 'tags': 'matthew' },
        { '$addToSet': { 'tags': 'dataset2' } }
    ))
    requests.append(UpdateMany(
        { 'tags': { '$all': ['matthew', 'dataset2'] } },
        { '$pull': { 'tags': 'matthew' } }
    ))
    requests.append(UpdateMany(
        { 'tags': 'gabby' },
        { '$addToSet': { 'tags': 'dataset1' } }
    ))
    requests.append(UpdateMany(
        { 'tags': { '$all': ['gabby', 'dataset1'] } },
        { '$pull': { 'tags': 'gabby' } }
    ))

    print('Updating database...')
    response = collection.bulk_write(requests)
    print(f'Modified: {response.modified_count}')

if __name__ == '__main__':
    main()
