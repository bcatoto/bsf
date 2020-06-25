from paiper.loader import load_articles
from paiper.classifier import Classifier

# comment out lines that are not relevant on an as-needed basis
# use this for debugging
def main():
    # load_articles()
    classifier = Classifier()
    classifier.train_model('matthew')
    # classifier.load_vectorizer(vectorizer_name)
    # classifier.load_model(model_name)
    # classifier.predict(abstracts)

if __name__ == "__main__":
    main()