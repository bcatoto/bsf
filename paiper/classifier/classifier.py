from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from pymongo import MongoClient
import pickle
import os
import random

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
VECTORIZERS_PATH = os.path.join(os.path.dirname(__file__), 'vectorizers')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')

class Classifier:

    def train_model(self, collection, training_size=0.8, save_pickle=True, doc2vec=False):
        """
        Trains Classifier based on set of relevant and irrelevant article abstracts
        (from MongoDB database)
        Features: preprocessed abstracts
        Values: relevant (1) or irrelevant (0)

        :param collection: name of MongoDB collection of articles to train model on
        :param training_size: percentage of articles to go in training set,
        remainder will go in testing set
        :param doc2vec: (not yet used) Bool flag to use doc2vec instead of tfidf
        """
        # queries database
        db = MongoClient(DATABASE_URL).classifier
        articles = list(db[collection].find())
        random.shuffle(articles)

        training_abs = []
        training_val = []
        testing_abs = []
        testing_val = []

        # separates articles into training and testing set based on specified
        # training size
        limit = int(training_size * len(articles))

        for i, article in enumerate(articles):
            if i < limit:
                training_abs.append(article['processed_abstract'])
                training_val.append(1 if article['relevant'] else 0)
            else:
                testing_abs.append(article['processed_abstract'])
                testing_val.append(1 if article['relevant'] else 0)

        # vectorize abstracts
        vectorizer = TfidfVectorizer()
        training_feat = vectorizer.fit_transform(training_abs)
        testing_feat = vectorizer.transform(testing_abs)

        # train model
        model = LogisticRegression()
        model.fit(training_feat, training_val)

        # scores model based on accuracy of testing set
        testing_pred = model.predict(testing_feat)
        score = model.score(testing_feat, testing_val)
        print(f'{collection} model accuracy: {score}')
        print(classification_report(testing_val, testing_pred))

        # pickles vectorizer and model and saves to respective folders
        if save_pickle:
            with open(os.path.join(VECTORIZERS_PATH, f'{collection}_{round(score * 100)}_vectorizer.pkl'), 'wb') as file:
                pickle.dump(vectorizer, file)
            with open(os.path.join(MODELS_PATH, f'{collection}_{round(score * 100)}_model.pkl'), 'wb') as file:
                pickle.dump(model, file)

        self._vectorizer = vectorizer
        self._model = model

    def load_vectorizer(self, vectorizer_name):
        """
        Loads given vectorizer from vectorizer folder
        :param vectorizer_name: name of vectorizer to load into Classifier
        """
        with open(os.path.join(VECTORIZERS_PATH, vectorizer_name), 'rb') as file:
            self._vectorizer = pickle.load(file)

    def load_model(self, model_name):
        """
        Loads given model from models folder
        :param model_name: name of model to load into Classifier
        """
        with open(os.path.join(MODELS_PATH, model_name), 'rb') as file:
            self._model = pickle.load(file)

    def predict(self, abstracts):
        """
        Vectorizes the abstracts (in list form) and returns predictions of model on features
        :param features: article abstracts to be classified as relevant or irrelevant
        based on model of Classifier
        """
        features = self._vectorizer.transform(abstracts)
        return self._model.predict(features)
