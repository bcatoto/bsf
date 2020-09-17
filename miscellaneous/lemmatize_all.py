from pymongo import MongoClient
import spacy
import json
import os

"""
Additional script to take abstracts from a MongoDB collection and perform additional data cleaning
1. Convert any British spellings to American spellings (e.g. replace "colour" to "color")
2. Lemmatize words (e.g. convert "done" to "do", "flavors" to "flavor") 
3. Remove stop words (e.g. eliminate "and", "the", "of", "is", etc.) 
Running this script on a corpus of 3.5 million abstracts reduced the file size from 4.0 to 3.1 GB.
"""

tag = "dataset1"
DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

print('Getting articles...')
collection = MongoClient(DATABASE_URL).abstracts.all
articles = list(collection.find(
    { 'tags': tag },
    { 'processed_abstract' : 1, '_id': 0 },
))
print(f'Number of articles: {len(articles)}.')

# get abstracts only, to speed up processing
abstracts = []
for article in articles:
    abstracts.append(article['processed_abstract'])
articles = None
print('Stored all processed abstracts into a list')

# process the abstracts
cleaned_abstracts = []
nlp = spacy.load("en_core_web_sm", disable=['tagger', 'parser', 'ner'])

# load GB to US dictionary
with open('miscellaneous/us_gb_dict.txt', 'r') as convert:
    spelling = json.load(convert)
print('Stored json dictionary in memory')

# clean abstracts
for abstract in nlp.pipe(abstracts, batch_size=1000, n_process=4):
    this_abstract = " ".join([token.lemma_ for token in abstract if not token.is_stop])
    for gb, us in spelling.items():
        this_abstract = this_abstract.replace(gb, us)
    cleaned_abstracts.append(this_abstract)
abstracts = None
print('Processing done. Storing...')

# write abstracts to file, to be 
with open('abstracts.txt', 'w') as file:
   file.write('\n+++\n'.join(cleaned_abstracts))
print('Done')