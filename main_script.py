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
    # classifier = Classifier()
    classifiers = [Classifier(), Classifier()]

    # EITHER LOAD GABBY OR MATTHEW
    # classifier.load_vectorizer('gabby_vectorizer.pkl')
    # classifier.load_model('gabby_model.pkl')
    # classifier.load_vectorizer('matthew_vectorizer.pkl')
    # classifier.load_model('matthew_model.pkl')
    classifiers[0].load_vectorizer('gabby_vectorizer.pkl')
    classifiers[0].load_model('gabby_model.pkl')
    classifiers[1].load_vectorizer('matthew_vectorizer.pkl')
    classifiers[1].load_model('matthew_model.pkl')

    # TAGS
    tags = ['gabby', 'matthew']

    query = 'lamb flavor compounds'

    # SPRINGER SCRAPER
    springer = SpringerScraper(tags, classifiers)
    springer.scrape(keyword=query)

    # PUBMED SCRAPER
    pubmed = PubmedScraper(tags, classifiers)
    pubmed.scrape(query)

    # ELSEVIER SCRAPER
    elsevier = ElsevierScraper(tags, classifiers)
    elsevier.scrape(query)

if __name__ == '__main__':
    main()
