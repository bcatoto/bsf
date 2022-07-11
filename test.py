import os
from pymongo import MongoClient

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
client = MongoClient(DATABASE_URL)


print(client.list_database_names())

db = client.classifier

print(db.list_collection_names())
