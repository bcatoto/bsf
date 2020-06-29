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
    classifier.load_vectorizer('gabby_vectorizer.pkl')
    classifier.load_model('gabby_model.pkl')
    # classifier.load_vectorizer('gabby_vectorizer.pkl')
    # classifier.load_model('gabby_model.pkl')

    # ELSEVIER SCRAPER
    elsevier = ElsevierScraper(collection='gabby', classifier=classifier)
    elsevier.scrape('duck flavor compounds')

    # SPRINGER SCRAPER
    # springer = SpringerScraper(collection='gabby', classifier=classifier)
    # springer.scrape(keyword='fats')

    # PUBMED SCRAPER
    # pubmed = PubmedScraper(collection='gabby', classifier=classifier)
    # pubmed.scrape('lamb flavor compounds')

if __name__ == '__main__':
    main()
