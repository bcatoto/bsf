from paiper.processor import MaterialsTextProcessor
from pymongo import MongoClient, UpdateOne, DeleteOne
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
from progress.bar import ChargingBar
import spacy
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

class Food2Vec:

    def __init__(self, tag):
        """
        Initializes collection
        :param tag: name of tag to filter articles for model training
        """
        self.tag = tag
        self._collection = MongoClient(DATABASE_URL).abstracts.all

    def update_abstracts(self):
        """
        Converts processed abstracts in database so that they are segmented by sentence
        """
        processor = MaterialsTextProcessor()
        nlp = spacy.load('en_core_web_sm')

        print('Getting abstracts...')
        articles = list(self._collection.find({}, { 'abstract': 1 }))

        # charging bar
        bar = ChargingBar(f'Updating abstracts:', max=len(articles), suffix='%(index)d of %(max)d')

        requests = []
        delete = []

        for article in articles:
            doc = nlp(article['abstract'])

            # rebuild each sentence by applying Mat2Vec tokenizer and joining tokens with spaces
            sents = []
            for sent in doc.sents:
                try:
                    tokens, materials = processor.process(sent.text)
                except OverflowError:
                    requests.append(DeleteOne({ '_id': article['_id'] }))
                    continue

                processed_sent = ' '.join(tokens)
                sents.append(processed_sent)

            # ensure that each sentence is on a new line (required for Word2Vec)
            processed_abstract = '\n'.join(sents)

            # modifies existing document to include tag
            requests.append(UpdateOne(
                { '_id' : article['_id'] },
                { '$set': { 'processed_abstract': processed_abstract } }
            ))
            bar.next()
        bar.finish()

        # update MongoDB
        print(f'Updating collection...')
        if requests:
            mongo = self._collection.bulk_write(requests)
            print(f'Modified: {mongo.modified_count}.')


    def train_model(self):
        """
        Trains word2vec model for given tag
        """
        articles = list(self._collection.find({'tags': self.tag}))
        abstracts = []
        print('Getting articles...')
        for article in articles:
            abstracts.append(article['processed_abstract'])
        sentences = '\n'.join(abstracts)
        
        # writes out corpus to text file
        print('Printing corpus...')
        with open('corpus.txt', mode='w', encoding='utf8') as outFile:
            outFile.write(sentences)
        with open('corpus.txt', mode='r') as outFile:
            print('Training model. This could take a while...')
            sentences = LineSentence(outFile)
            model = Word2Vec(
                sentences,
                window=8,
                min_count=5,
                workers=16,
                negative=15,
                iter=30
            )
        
        # no file extension necessary
        model.save(f'{self.tag}_word2vec')
        print('Model saved!')

    def load_model(self):
        """
        Loads the specific word2vec model for given tag and prints similarity (change this later)
        """
        print(f'Loading model: {self.tag}...')
        model = Word2Vec.load(f'{self.tag}_word2vec')
        print('Similarity of \'flavor\' and \'food\':', model.similarity('flavor', 'food'))
