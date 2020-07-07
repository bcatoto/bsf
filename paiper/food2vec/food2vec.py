from paiper.processor import MaterialsTextProcessor
from pymongo import MongoClient, UpdateOne, DeleteOne
from gensim.models import Word2Vec
from gensim.models.word2vec import LineSentence
from progress.bar import ChargingBar
import spacy
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')
CORPUS_PATH = os.path.join(os.path.dirname(__file__), 'corpus.txt')

class Food2Vec:

    def __init__(self, tag, collection = 'all'):
        """
        Initializes collection
        :param tag: name of tag to filter articles for model training
        """
        self.tag = tag
        self._collection = MongoClient(DATABASE_URL).abstracts[collection]

    def train_model(self, save=True):
        """
        Trains word2vec model for given tag
        """
        print('Getting articles...')
        articles = list(self._collection.find(
            { 'tags': self.tag },
            { 'processed_abstract' : 1, '_id': 0 }
        ))
        abstracts = []
        for article in articles:
            abstracts.append(article['processed_abstract'])
        sentences = '\n'.join(abstracts)

        # writes out corpus to text file
        print('Printing corpus...')
        with open(CORPUS_PATH, mode='w', encoding='utf8') as outFile:
            outFile.write(sentences)

        # trains word2vec model
        with open(CORPUS_PATH, mode='r') as inFile:
            print('Training model...')
            sentences = LineSentence(inFile)
            model = Word2Vec(
                sentences,
                window=8,
                min_count=5,
                workers=16,
                negative=15,
                iter=30
            )
        os.remove(CORPUS_PATH)

        # saves model
        if save:
            model.save(os.path.join(MODELS_PATH, self.tag))
        self._model = model

        print('Model saved.')

    def load_model(self):
        """
        Loads the specific word2vec model associated with tag
        """
        self._model = Word2Vec.load(self.tag)

    def most_similar(query, topn=1):
        """
        Return terms most similar to query
        :param query: term to compare similarity to
        :topn: default to 1, number of terms returned in order of most similar
        """
        print(self._model.wv.most_similar(query, topn=topn))
