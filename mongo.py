from pymongo import MongoClient, UpdateOne
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

def main():
    collection = MongoClient(DATABASE_URL).abstracts.all

    print('Removing \'gabby\'')
    print('Getting documents...')
    docs = collection.find({ 'tags': { '$all': ['gabby', 'dataset1'] } })

    print('Updating documents...')
    requests = []
    for doc in docs:
        requests.append(UpdateOne(
            doc,
            { '$pull': { 'tags': 'gabby' } }
        ))
    response = collection.bulk_write(requests)
    print(f'Modified: {response.modified_count}')
    print()

    print('Converting \'gabby\' to \'dataset1\'')
    print('Getting documents...')
    docs = collection.find({ 'tags': 'gabby' })

    requests = []
    for doc in docs:
        requests.append(UpdateOne(
            doc,
            {
                '$pull': { 'tags': 'gabby' },
                '$addToSet': { 'tags': 'dataset1' }
            }
        ))
    response = collection.bulk_write(requests)
    print(f'Modified: {response.modified_count}')
    print()

    print('Removing \'matthew\'')
    print('Getting documents...')
    docs = collection.find({ 'tags': { '$all': ['matthew', 'dataset2'] } })

    print('Updating documents...')
    requests = []
    for doc in docs:
        requests.append(UpdateOne(
            doc,
            { '$pull': { 'tags': 'matthew' } }
        ))
    response = collection.bulk_write(requests)
    print(f'Modified: {response.modified_count}')
    print()

    print('Converting \'matthew\' to \'dataset2\'')
    print('Getting documents...')
    docs = collection.find({ 'tags': 'matthew' })

    requests = []
    for doc in docs:
        requests.append(UpdateOne(
            doc,
            {
                '$pull': { 'tags': 'matthew' },
                '$addToSet': { 'tags': 'dataset2' }
            }
        ))
    response = collection.bulk_write(requests)
    print(f'Modified: {response.modified_count}')
    print()

if __name__ == '__main__':
    main()
