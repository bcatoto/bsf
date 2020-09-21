from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn import model_selection
from sklearn import utils
from pymongo import MongoClient
import pickle
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
VECTORIZERS_PATH = os.path.join(os.path.dirname(__file__), 'vectorizers')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')

class Classifier:

    def __init__(self, tag):
        """
        Initializes Classifier class with given tag

        :param tag: name of tag to filter articles for model training
        """
        self.tag = tag
        self.reset_metrics()

    def train(self, database_name='classifier', collection_name=None, vectorizer_name=None, model_name=None, training_size=0.8, random_state=5):
        """
        Trains Classifier based on set of relevant and irrelevant article abstracts
        Features: preprocessed abstracts (in vector form)
        Values: relevant (1) or irrelevant (0)

        :param database_name: defaults to 'classifier', database to get training data from
        :param collection_name: defaults to tag, collection to get training data from
        :param vectorizer_name: defaults to tag, name of vectorizer file
        :param model_name: defaults to tag, name of model file
        :param training_size: defaults to 0.8, percentage of articles to go in
        training set, remainder will go in testing set
        :param random_state: defaults to 5, controls random number generator of
        training and testing set splitter
        """
        # initializes optional arguments to tag
        if collection_name is None:
            collection_name = self.tag
        if vectorizer_name is None:
            vectorizer_name = self.tag
        if model_name is None:
            model_name = self.tag

        print(f'Collection: {database_name}.{collection_name}.')

        # queries relevant collection of MongoDB database
        collection = MongoClient(DATABASE_URL)[database_name][collection_name]
        articles = list(collection.find())

        # fill abstracts and values lists
        abstracts = []
        values = []
        for article in articles:
            abstracts.append(article['processed_abstract'])
            values.append(1 if article['relevant'] else 0)

        # split into training and testing data
        # good random_state results (for Matthew): 3 (0.95) and 5 (0.975)
        train_abs, test_abs, train_val, test_val = model_selection.train_test_split(abstracts, values, train_size=training_size, random_state=random_state)

        # vectorize abstracts
        vectorizer = TfidfVectorizer()
        train_feat = vectorizer.fit_transform(train_abs)
        test_feat = vectorizer.transform(test_abs)

        # train model
        model = LogisticRegression()
        model.fit(train_feat, train_val)

        # scores model based on accuracy of testing set
        test_pred = model.predict(test_feat)
        score = model.score(test_feat, test_val)
        print(f'{self.tag} model accuracy: {score}')
        print(classification_report(test_val, test_pred))

        # pickles vectorizer and model and saves to respective folders
        vec_filename = os.path.join(VECTORIZERS_PATH, f'{vectorizer_name}.pkl')
        with open(vec_filename, 'wb') as file:
            pickle.dump(vectorizer, file)

        model_filename = os.path.join(MODELS_PATH, f'{model_name}.pkl')
        with open(model_filename, 'wb') as file:
            pickle.dump(model, file)

        self._vectorizer = vectorizer
        self._model = model

    def load(self, vectorizer_name=None, model_name=None):
        """
        Loads vectorizer from vectorizers folder
        Loads model from models folder
        :param vectorizer_name: defaults to tag, name of vectorizer file to load
        :param model_name: defaults to tag, name of model file to load
        """
        # initializes optional arguments to tag
        if vectorizer_name is None:
            vectorizer_name = self.tag
        
        if model_name is None:
            model_name = self.tag

        # loads vectorizer
        filename = os.path.join(VECTORIZERS_PATH, f'{vectorizer_name}.pkl')
        with open(filename, 'rb') as file:
            self._vectorizer = pickle.load(file)
        
        # loads model
        filename = os.path.join(MODELS_PATH, f'{model_name}.pkl')
        with open(filename, 'rb') as file:
            self._model = pickle.load(file)

    def predict(self, abstracts):
        """
        Vectorizes the abstracts (in list form) and returns predictions of model on features

        :param abstracts: article abstracts to be classified as relevant or irrelevant
        based on model of Classifier
        """

        # TODO: add validation to ensure model was loaded before prediction

        features = self._vectorizer.transform(abstracts)
        return self._model.predict(features)

    def reset_metrics(self):
        self.total = 0
        self.relevant = 0
        self.irrelevant = 0

    def print_metrics(self):
        print(f'Total articles analyzed: {self.total}.')
        print(f'Stored {self.relevant} new abstracts relevant to \'{self.tag}\'.')
        print(f'Ignored {self.irrelevant} abstracts irrelevant to \'{self.tag}\'.')
        print(f'Ignored {self.total - self.relevant - self.irrelevant} articles already tagged as \'{self.tag}\'.')
        print()
