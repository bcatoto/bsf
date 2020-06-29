from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.springer import SpringerScraper

# comment out lines that are not relevant on an as-needed basis
# use this for debugging
def main():
    # load_articles()

    # CLASSIFIER
    classifier = Classifier()
    # classifier.train_model('gabby')
    classifier.load_vectorizer('gabby_vectorizer.pkl')
    classifier.load_model('gabby_model.pkl')
    # classifier.load_vectorizer('gabby_vectorizer.pkl')
    # classifier.load_model('gabby_model.pkl')

    # SPRINGER SCRAPER
    springer = SpringerScraper(collection='gabby', classifier=classifier)
    springer.scrape(keyword='duck')

    # springer_scraper('gabby', classifier, keyword='duck')
    # elsevier_scraper('gabby', classifier, query='flavor compounds')
    # pubmed_scraper('gabby', classifier, term='flavor compounds')

if __name__ == '__main__':
    main()
