from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.elsevier import ElsevierScraper
from paiper.scraper.springer import SpringerScraper
from paiper.scraper.pubmed import PubmedScraper

# comment out lines that are not relevant on an as-needed basis
# use this for debugging
def main():
    # load_articles()

    # CLASSIFIER
    classifier = Classifier()
    # classifier.train_model('gabby')

    # EITHER LOAD GABBY OR MATTHEW
    classifier.load_vectorizer('gabby_vectorizer.pkl')
    classifier.load_model('gabby_model.pkl')
    # classifier.load_vectorizer('matthew_vectorizer.pkl')
    # classifier.load_model('matthew_model.pkl')

    query = 'veal flavor compounds'

    # ELSEVIER SCRAPER
    # elsevier = ElsevierScraper('gabby', classifier)
    # elsevier.scrape(query)

    # SPRINGER SCRAPER
    springer = SpringerScraper('gabby', classifier)
    springer.scrape(subject='Food Science')

    # PUBMED SCRAPER
    # pubmed = PubmedScraper('gabby', classifier)
    # pubmed.scrape(query)

if __name__ == '__main__':
    main()
