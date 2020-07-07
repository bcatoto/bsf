from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.elsevier import ElsevierScraper
from paiper.scraper.springer import SpringerScraper
from paiper.scraper.pubmed import PubmedScraper
from word2vec import Food2Vec # consider renaming word2vec.py to food2vec.py
import argparse
import os

KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), 'paiper/scraper/keywords/keywords.txt')

def main():
    # SET UP PARSER
    parser = argparse.ArgumentParser(description='Scrape abstracts')
    parser.add_argument('-l', '--load', action='store_true', help='loads training data into database')
    parser.add_argument('-t', '--train', action='store_true', help='trains classifier models')
    parser.add_argument('-q', '--query', type=str, default='', help='database query (requires quotation marks)')
    parser.add_argument('-u', '--subject', type=str, default='', help='Springer Nature subject query (requires quotation marks)')
    parser.add_argument('-f', '--file', action='store_true', help='opens keywords.txt and scrapes for each keyword, one at a time')
    parser.add_argument('-c', '--collection', type=str, default='all', help='collection to store abstracts in')
    parser.add_argument('-a', '--all', action='store_true', help='queries all databases')
    parser.add_argument('-s', '--springer', action='store_true', help='queries Springer Nature database')
    parser.add_argument('-p', '--pubmed', action='store_true', help='queries PubMed database')
    parser.add_argument('-e', '--elsevier', action='store_true', help='queries Elsevier database')
    parser.add_argument('-w', '--word2vec_train', action='store_true', help='trains word2vec models')
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

    # USE ALL SCRAPERS
    if args.all:
        args.springer = args.pubmed = args.elsevier = True

    # READ QUERIES FROM FILE
    if args.file:
        print('Loading keywords from file...')
        keywords = []
        with open(KEYWORDS_PATH, 'r') as queries:
            keywords = [word.strip() for word in queries]
        for keyword in keywords:
            if args.springer:
                springer = SpringerScraper(classifiers, collection=args.collection)
                springer.scrape(subject=args.subject, keyword=keyword)
            if args.pubmed:
                pubmed = PubmedScraper(classifiers, collection=args.collection)
                pubmed.scrape(keyword)
            if args.elsevier:
                elsevier = ElsevierScraper(classifiers, collection=args.collection)
                elsevier.scrape(keyword)

    # USE QUERY FROM COMMAND LINE
    else:
        # SPRINGER SCRAPER
        if args.springer:
            springer = SpringerScraper(classifiers, collection=args.collection)
            springer.scrape(subject=args.subject, keyword=args.query)

        # PUBMED SCRAPER
        if args.pubmed:
            pubmed = PubmedScraper(classifiers, collection=args.collection)
            pubmed.scrape(args.query)

        # ELSEVIER SCRAPER
        if args.elsevier:
            elsevier = ElsevierScraper(classifiers, collection=args.collection)
            elsevier.scrape(args.query)

    
    # food2vec_model.update_abstracts() --> don't need to run this since scrapers were updated
    food2vec_models = [Food2Vec('gabby'), Food2Vec('matthew')]
    
    # RUN WORD2VEC
    if args.word2vec_train:
        food2vec_models[0].train_model()
        # food2vec_models[1].train_model()
    else:
        food2vec_models[0].load_model()
        food2vec_models[1].load_model()


if __name__ == '__main__':
    main()
