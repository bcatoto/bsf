from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.elsevier import ElsevierScraper
from paiper.scraper.springer import SpringerScraper
from paiper.scraper.pubmed import PubmedScraper
import argparse

def main():
    # SET UP PARSER
    parser = argparse.ArgumentParser(description='Scrape abstracts')
    parser.add_argument('-l', '--load', action='store_true', help='loads training data into database')
    parser.add_argument('-t', '--train', action='store_true', help='trains classifier models')
    parser.add_argument('-q', '--query', type=str, default='', help='database query (requires quotation marks)')
    parser.add_argument('-u', '--subject', type=str, default='', help='Springer Nature subject query (requires quotation marks)')
    parser.add_argument('-a', '--all', action='store_true', help='queries all databases')
    parser.add_argument('-s', '--springer', action='store_true', help='queries Springer Nature database')
    parser.add_argument('-p', '--pubmed', action='store_true', help='queries PubMed database')
    parser.add_argument('-e', '--elsevier', action='store_true', help='queries Elsevier database')
    args = parser.parse_args()

    # LOAD TRAINING DATA
    if args.load:
        load_articles()

    # CLASSIFIER
    classifiers = [Classifier('gabby'), Classifier('matthew')]
    if args.train:
        classifiers[0].train_model()
        classifiers[1].train_model()
    else:
        classifiers[0].load_vectorizer('gabby_vectorizer.pkl')
        classifiers[0].load_model('gabby_model.pkl')
        classifiers[1].load_vectorizer('matthew_vectorizer.pkl')
        classifiers[1].load_model('matthew_model.pkl')

    # SPRINGER SCRAPER
    if args.all or args.springer:
        springer = SpringerScraper(classifiers)
        springer.scrape(subject=args.subject, keyword=args.query)

    # PUBMED SCRAPER
    if args.all or args.pubmed:
        pubmed = PubmedScraper(classifiers)
        pubmed.scrape(args.query)

    # ELSEVIER SCRAPER
    if args.all or args.elsevier:
        elsevier = ElsevierScraper(classifiers)
        elsevier.scrape(args.query)

if __name__ == '__main__':
    main()
