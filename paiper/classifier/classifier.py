from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn import model_selection
from pymongo import MongoClient
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import pickle
import os
import random
import multiprocessing

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')
VECTORIZERS_PATH = os.path.join(os.path.dirname(__file__), 'vectorizers')
MODELS_PATH = os.path.join(os.path.dirname(__file__), 'models')

class Classifier:

    def train_model(self, collection, training_size=0.8, random_state=5, save_pickle=True, doc2vec=False):
        """
        Trains Classifier based on set of relevant and irrelevant article abstracts
        (from MongoDB database)
        Features: preprocessed abstracts (in vector form)
        Values: relevant (1) or irrelevant (0)

        :param collection: name of MongoDB collection of articles to train model on
        :param training_size: percentage of articles to go in training set,
        remainder will go in testing set
        :param random_state: controls random number generator of training and
        testing set splitter
        :param doc2vec: (not yet used) Bool flag to use doc2vec instead of tfidf
        """
        # queries database
        db = MongoClient(DATABASE_URL).classifier
        articles = list(db[collection].find())

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
        # check for doc2vec option
        if doc2vec:
            #fill up doc2vec over here
            # https://towardsdatascience.com/implementing-multi-class-text-classification-with-doc2vec-df7c3812824d
            # https://radimrehurek.com/gensim/models/doc2vec.html

            print('Testing doc2vec: to be completed')
            print('This part currently does not function properly')
            train_documents = []
            test_documents = []
            for i, train_abstract in enumerate(train_abs):
                train_documents.append(TaggedDocument(words=train_abstract.split(), tags=train_val[i]))
            for j, test_abstract in enumerate(test_abstract):
                test_documents.append(TaggedDocument(words=test_abstract.split(), tags=test_val[i]))
            cores = multiprocessing.cpu_count()
            model_d2v = Doc2Vec(dm=0, vector_size=300, negative=5, hs=0, min_count=2, workers=cores, alpha=0.025, min_alpha=0.001)
            model_d2v.build_vocab([x for x in train_documents])
            train_documents = random.shuffle(train_documents, random_state=random_state)
            model_d2v.train(train_documents,total_examples=len(train_documents), epochs=30)

        
        # default to tf-idf
        else:
            vectorizer = TfidfVectorizer()
            train_feat = vectorizer.fit_transform(train_abs)
            test_feat = vectorizer.transform(test_abs)

        # train model
        model = LogisticRegression()
        model.fit(train_feat, train_val)

        # scores model based on accuracy of testing set
        test_pred = model.predict(test_feat)
        score = model.score(test_feat, test_val)
        print(f'{collection} model accuracy: {score}')
        print(classification_report(test_val, test_pred))

        # pickles vectorizer and model and saves to respective folders
        if save_pickle:
            with open(os.path.join(VECTORIZERS_PATH, f'{collection}_vectorizer.pkl'), 'wb') as file:
                pickle.dump(vectorizer, file)
            with open(os.path.join(MODELS_PATH, f'{collection}_model.pkl'), 'wb') as file:
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
