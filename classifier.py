# https://medium.com/machine-learning-intuition/document-classification-part-2-text-processing-eaa26d16c719
# https://stackabuse.com/overview-of-classification-methods-in-python-with-scikit-learn/
# TODO Idea: for each abstract that we scrape, first check if it's relevant before adding it to MongoDB

# import statements
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from pymongo import MongoClient
from sys import argv, stderr
import os

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

def main():
    if len(argv) < 2:
        print('Collection not specified', file=stderr)

    # queries database
    db = MongoClient(DATABASE_URL).training
    articles = list(db[argv[1]].find())

    # gets abstracts and values
    training_abs = []
    training_val = []
    testing_abs = []
    testing_val = []

    # put fake values
    for i, article in enumerate(articles):
        if i < int(len(articles) / 5):
            testing_abs.append(article['processed_abstract'])
            testing_val.append(1 if (i % 2 == 0) else 0)
        else:
            training_abs.append(article['processed_abstract'])
            training_val.append(1 if (i % 2 == 0) else 0)

    # vectorize abstracts
    vectorizer = TfidfVectorizer()
    training_feat = vectorizer.fit_transform(training_abs)
    testing_feat = vectorizer.fit_transform(testing_abs)

    # train model
    logreg_clf = LogisticRegression()
    logreg_clf.fit(training_feat, training_val)

    # scores model based on accuracy of testing set
    # not sure about this part, getting weird errors
    score = logreg_clf.score(testing_feat, testing_val)
    print(score)

if __name__ == '__main__':
    main()
