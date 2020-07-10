from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.elsevier import ElsevierScraper
from paiper.scraper.springer import SpringerScraper
from paiper.scraper.pubmed import PubmedScraper
from paiper.food2vec import Food2Vec
import argparse
import os

KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), 'paiper/scraper/keywords')

def main():
    # set up parser
    parser = argparse.ArgumentParser(description='Scrape abstracts')
    parser.add_argument('-l', '--load', action='store_true', help='loads training data into database')
    parser.add_argument('-c', '--classifier', action='store_true', help='trains classifiers')
    parser.add_argument('--keywords', type=str, help='opens text file of keywords and scrapes for each keyword')
    parser.add_argument('--query', type=str, default='', help='database query (requires quotation marks)')
    parser.add_argument('--subject', type=str, default='', help='Springer Nature subject query (requires quotation marks)')
    parser.add_argument('--collection', type=str, default='all', help='collection to store scraped abstracts in')
    parser.add_argument('-o', '--store', action='store_true', help='stores all scraped abstracts in general tag')
    parser.add_argument('-a', '--all', action='store_true', help='scrapes all databases')
    parser.add_argument('-s', '--springer', action='store_true', help='scrapes Springer Nature database')
    parser.add_argument('-p', '--pubmed', action='store_true', help='scrapes PubMed database')
    parser.add_argument('-e', '--elsevier', action='store_true', help='scrapes Elsevier database')
    parser.add_argument('-f', '--food2vec', action='store_true', help='initializes word2vec models')
    parser.add_argument('-t', '--train', action='store_true', help='trains word2vec models')
    parser.add_argument('--similar', type=str, default='', help='food2vec model similarity query (requires quotation marks)')
    args = parser.parse_args()

    # load training data
    if args.load:
        load_articles()

    # classifier
    classifiers = [Classifier('gabby'), Classifier('matthew')]
    for classifier in classifiers:
        if args.classifier:
            classifier.train_model()
        else:
            classifier.load_vectorizer()
            classifier.load_model()

    # use all scrapers
    if args.all:
        args.springer = args.pubmed = args.elsevier = True

    # read queries from keywords.txt
    if args.keywords:
        print(f'Loading keywords from \'{args.keywords}\' file...')

        keywords = []
        with open(os.path.join(KEYWORDS_PATH, f'{args.keywords}.txt'), 'r') as queries:
            keywords = [word.strip() for word in queries]
            
        for keyword in keywords:
            if args.springer:
                springer = SpringerScraper(classifiers, collection=args.collection, save_all=args.store)
                springer.scrape(subject=args.subject, keyword=keyword)
            if args.pubmed:
                pubmed = PubmedScraper(classifiers, collection=args.collection, save_all=args.store)
                pubmed.scrape(keyword)
            if args.elsevier:
                elsevier = ElsevierScraper(classifiers, collection=args.collection, save_all=args.store)
                elsevier.scrape(keyword)

    # use query from command line
    else:
        # springer scraper
        if args.springer:
            springer = SpringerScraper(classifiers, collection=args.collection, save_all=args.store)
            springer.scrape(subject=args.subject, keyword=args.query)

        # pubmed scraper
        if args.pubmed:
            pubmed = PubmedScraper(classifiers, collection=args.collection, save_all=args.store)
            pubmed.scrape(args.query)

        # elsevier scraper
        if args.elsevier:
            elsevier = ElsevierScraper(classifiers, collection=args.collection, save_all=args.store)
            elsevier.scrape(args.query)

    # run word2vec
    if args.food2vec:
        models = [Food2Vec('gabby', collection=args.collection), Food2Vec('matthew', collection=args.collection)]
        for model in models:
            if args.train:
                model.train_model()
            else:
                model.load_model()
            model.load_phraser()

            # similarity
            if args.similar:
                model.most_similar(args.similar, topn=5)
            model.most_similar('flavor compounds', topn=5)
            model.most_similar('flavor', topn=5)
            model.most_similar('beef', topn=5)
            model.most_similar('duck meat', topn=5)
            model.most_similar('lamb', topn=5)

            # analogy
            model.analogy('pig', 'cow', 'beef')
            model.analogy('chicken', 'cow', 'beef')
            model.analogy('chicken', 'pig', 'pork')
            model.analogy('soy', 'beef', 'hemoglobin')
            print()

if __name__ == '__main__':
    main()
