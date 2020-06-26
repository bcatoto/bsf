from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper import springer_scraper, elsevier_scraper, pubmed_scraper

# comment out lines that are not relevant on an as-needed basis
# use this for debugging
def main():
    # load_articles()
    classifier = Classifier()
    # classifier.train_model('matthew')
    classifier.load_vectorizer('matthew_98_vectorizer.pkl')
    classifier.load_model('matthew_98_model.pkl')
    # springer_scraper(classifier, keyword='animal feed')
    # elsevier_scraper(classifier, query='flavor compounds')
    pubmed_scraper(classifier, term='flavor compounds')

if __name__ == '__main__':
    main()
