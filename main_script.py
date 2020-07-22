from paiper.loader import load_articles
from paiper.classifier import Classifier
from paiper.scraper.elsevier import ElsevierScraper
from paiper.scraper.springer import SpringerScraper
from paiper.scraper.s2orc import S2ORCScraper
from paiper.scraper.pubmed import PubmedScraper
from paiper.food2vec import Food2Vec
import argparse
import os

KEYWORDS_PATH = os.path.join(os.path.dirname(__file__), 'paiper/scraper/keywords')

"""
Using the scraper:
We want to save all articles related to food science, regardless of classifier result
If you are running Gabby's keywords, then add the -o flag to your command
If you are running Matthew's keywords, then don't use the -o flag
If you are running a very generic term, don't use the -o flag
"""

"""
Reference:
gabby --> dataset1
matthew --> dataset2
"""

def main():
    # set up parser
    parser = argparse.ArgumentParser(description='Scrape abstracts')
    parser.add_argument('-l', '--load', action='store_true', help='loads training data into database')
    parser.add_argument('-c', '--classifier', action='store_true', help='trains classifiers')
    parser.add_argument('--keywords', type=str, help='opens file of keywords and scrapes for each keyword (specify ending)')
    parser.add_argument('--query', type=str, default='', help='database query (requires quotation marks)')
    parser.add_argument('--subject', type=str, default='', help='Springer Nature subject query (requires quotation marks)')
    parser.add_argument('--filename', type=str, default='', help='S2ORC filename')
    parser.add_argument('--collection', type=str, default='all', help='collection to store scraped abstracts in')
    parser.add_argument('-o', '--store', action='store_true', help='stores all scraped abstracts in general tag')
    parser.add_argument('-a', '--all', action='store_true', help='scrapes all databases')
    parser.add_argument('-s', '--springer', action='store_true', help='scrapes Springer Nature database')
    parser.add_argument('-r', '--s2orc', action='store_true', help='scrapes S2ORC data files')
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
    classifiers = [Classifier('dataset1'), Classifier('dataset2')]
    for classifier in classifiers:
        if args.classifier:
            classifier.train_model()
        else:
            classifier.load_vectorizer()
            classifier.load_model()

    # indicate that all abstracts will be saved
    if args.store:
        print('Store flag was marked. All abstracts scraped in this session will be saved.')
        print()

    # use all scrapers
    if args.all:
        args.springer = args.pubmed = args.elsevier = True

    # read queries from keywords.txt
    if args.keywords:
        print(f'Loading keywords from \'{args.keywords}\' file...')
        print()

        keywords = []
        with open(os.path.join(KEYWORDS_PATH, f'{args.keywords}'), 'r') as queries:
            keywords = [word.strip() for word in queries]

        # initialize each scraper once rather than after each keyword
        springer = SpringerScraper(classifiers, collection=args.collection, save_all=args.store)
        pubmed = PubmedScraper(classifiers, collection=args.collection, save_all=args.store)
        elsevier = ElsevierScraper(classifiers, collection=args.collection, save_all=args.store)

        for keyword in keywords:
            if args.springer:
                springer.scrape(subject=args.subject, keyword=keyword)
            if args.pubmed:
                pubmed.scrape(keyword)
            if args.elsevier:
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

        # S2ORC scraper
        if args.s2orc:
            s2orc = S2ORCScraper(classifiers, collection=args.collection, save_all=args.store)
            s2orc.scrape(filename=args.filename)

    # run word2vec
    if args.food2vec:
        models = [Food2Vec('dataset1'), Food2Vec('dataset2')]
        for model in models:
            if args.train:
                model.train_model(collection_name=args.collection)
            else:
                model.load_phraser()
                model.load_wv()

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
