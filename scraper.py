from pymongo import MongoClient
from bs4 import BeautifulSoup
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
from progress.bar import ChargingBar
import requests
import json
import re
import datetime
import os

SPRINGER_NATURE_API_KEY = os.environ.get('SPRINGER_NATURE_API_KEY', 'Springer key doesn\'t exist')
ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY', 'Elsevier key doesn\'t exist')
DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

PROCESSOR = MaterialsTextProcessor()

CLIENT = MongoClient(DATABASE_URL)
DB = CLIENT.abstracts

def get_value(data, key):
    try:
        return data[key]
    except KeyError:
        return None

def springer_url_builder(s, subject, keyword):
    """
    Builds url to query Springer Nature API
    :param s: start index of returned result
    :param subject: subject constraint query
    :param keyword: keyword constraint query
    """
    # builds query
    query = 'type:Journal'
    if subject:
        query += f'+subject:\"{subject}\"'
    if keyword:
        query += f'+keyword:\"{keyword}\"'

    # builds url
    return f'http://api.springernature.com/meta/v2/json?s={s}&p=100&q=({query})&api_key={SPRINGER_NATURE_API_KEY}'

def springer_get_creators(creators):
    """
    Turns list of dictionary of creators into list of creators
    :param creators: list of creators where each creator is inside a dictionary
    """
    list = []
    for creator in creators:
        list.append(creator['creator'])
    return list

def springer_get_url(urls):
    """
    Returns generic url to paper or first url from list of urls
    :param urls: list of urls where each url is inside a dictionary
    """
    if not urls:
        return None
    for url in urls:
        if url['format'] == '':
            return url['value']
    return urls[0]['value']

def springer_get_date(date):
    """
    Converts date into datetime object
    :param date: date formatted 'YYYY-MM-DD'
    """
    date_array = date.split('-')
    return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

def springer_scraper(collection_name, classifier, subject = '', keyword = ''):
    """
    Scrapes metadata of Springer Nature articles returned by subject and
    keyword query, processes abstracts, and stores relevant articles

    :param collection_name: name of collection to store abstracts and metadata
    :param classifier: classifier model to determine if abstracts are relevant
    :param subject: subject constraint query, if empty does not include subject
    constraint to query
    :param keyword: keyword constraint query, if empty does not include keyword
    constraint to query
    """
    articles = []
    abstracts = []
    already_stored = []
    page = 1
    total = 100

    # prints subject and query made
    subject_print = subject if subject else 'None'
    keyword_print = keyword if keyword else 'None'
    print(f'Database: Springer Nature, Subject: {subject_print}, Keyword: {keyword_print}')

    # progress bar
    bar = ChargingBar('Getting metadata:', max = total, suffix = '%(index)d of %(max)d')

    # sets up collection
    collection = DB[collection_name]

    while page <= total:
        url = springer_url_builder(page, subject, keyword)
        response = requests.get(url)

        if response.ok:
            data = json.loads(response.content)
            records = data['records']

            # updates total to total number of papers in query
            if page == 1:
                total = int(data['result'][0]['total'])
                bar.max = total

            # gets metadata
            for record in records:
                # checks if paper is already in database using doi
                doi = record['doi']
                if collection.count_documents({ 'doi': doi }, limit = 1):
                    already_stored.append(doi)
                else:
                    # processes abstract text using processor from mat2vec
                    abstract = get_value(record, 'abstract')

                    if not abstract:
                        bar.next()
                        continue

                    tokens, materials = PROCESSOR.process(record['abstract'])
                    processed_abstract = ' '.join(tokens)

                    # converts metadata to json format
                    article = {
                        'doi': doi,
                        'title': get_value(record, 'title'),
                        'abstract': get_value(record, 'abstract'),
                        'url': springer_get_url(get_value(record, 'url')),
                        'creators': springer_get_creators(get_value(record, 'creators')),
                        'publication_name': get_value(record, 'publicationName'),
                        'issn': get_value(record, 'issn'),
                        'eissn': get_value(record, 'eIssn'),
                        'publication_date': springer_get_date(get_value(record, 'publicationDate')),
                        'database': 'springer',
                        'processed_abstract': processed_abstract
                    }
                    articles.append(article)
                    abstracts.append(processed_abstract)
                bar.next()
        page += 100
    bar.finish()

    # already stored papers
    print(f'Already stored: {len(already_stored)}')
    for doi in already_stored:
        print(f'\t{doi}')

    store(collection, classifier, articles, abstracts)

def elsevier_get_date(date): # could potentially combine this with springer_get_date() since code is identical
    """
    Converts date into datetime object
    :param date: date formatted 'YYYY-MM-DD'
    """
    date_array = date.split('-')
    return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

def elsevier_get_creators(creators):
    """
    Turns list of dictionary of creators into list of creators and ignores extraneous data
    :param creators: list of creators where each creator is inside a dictionary
    """
    entries = []
    for entry in creators:
        entries.append(entry['$'])
    return entries

def elsevier_scraper(collection_name, classifier, query = ''):
    """
    Scrapes metadata of Elsevier (ScienceDirect) articles returned
    by query, processes abstracts, and stores relevant articles

    :param collection_name: name of collection to store abstracts and metadata
    :param classifier: classifier model to determine if abstracts are relevant
    :param query: Elsevier database query
    """
    print(f'Database: Science Direct, Query: {query}')

    # creates search url
    url = f'https://api.elsevier.com/content/search/sciencedirect?query={query}&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'

    # gets dois
    dois = []
    page = 0
    total = 5000

    # progress bar
    bar = ChargingBar('Getting DOIs:', max = 5000, suffix = '%(index)d of %(max)d')

    while page < total:
        response = requests.get(url)

        if response.ok:
            data = json.loads(response.content)['search-results']

            # updates total to total number of papers in query
            if page == 0:
                total = min(5000, int(data['opensearch:totalResults']))
                bar.max = total

            # stores dois
            for entry in data['entry']:
                dois.append(entry['prism:doi'])
                bar.next()

            # if current page is last page, break
            if data['link'][0]['@href'] == data['link'][3]['@href']:
                break

            # sets url to next page in search
            url = data['link'][-2]['@href']

        page += 25
    bar.finish()

    # stores metadata
    articles = []
    abstracts = []
    already_stored = []

    # sets up collection
    collection = DB[collection_name]

    # progress bar
    bar = ChargingBar('Getting metadata:', max = len(dois), suffix = '%(index)d of %(max)d')

    for doi in dois:
        url = f'https://api.elsevier.com/content/article/doi/{doi}?apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
        response = requests.get(url)

        if response.ok:
            data = json.loads(response.content)['full-text-retrieval-response']['coredata']

            # checks if paper is already in database using doi
            if collection.count_documents({ 'doi': doi }, limit = 1):
                already_stored.append(doi)
            else:
                # processes abstract text using processor from mat2vec
                tokens, materials = PROCESSOR.process(data['dc:description'])
                processed_abstract = ' '.join(tokens)

                # converts metadata to json format
                article = {
                    'doi': doi,
                    'title': get_value(data, 'dc:title'),
                    'abstract': get_value(data, 'dc:description'),
                    'url': get_value(data, 'prism:url'),
                    'creators': elsevier_get_creators(get_value(data, 'dc:creator')),
                    'publication_name': get_value(data, 'prism:publicationName'),
                    'issn': get_value(data, 'prism:issn'),
                    'publication_date': elsevier_get_date(get_value(data, 'prism:coverDate')),
                    'database': 'ScienceDirect',
                    'processed_abstract': processed_abstract
                }
                articles.append(article)
                abstracts.append(processed_abstract)
        bar.next()
    bar.finish()

    # already stored
    print(f'Already stored: {len(already_stored)}')
    for doi in already_stored:
        print(f'\t{doi}')

    store(collection, classifier, articles, abstracts)

def pubmed_remove_html(element):
    """
    Removes HTML formatting from contents of field
    :param element: HTML/XML element of field
    """
    if not element:
        return None
    string = ''
    for content in element.contents:
        string += re.sub('\s*\<[^)]*\>', '', str(content))
    return string

def pubmed_get_authors(authors):
    """
    Turns XML element of authors into list of authors
    :param authors: XML element containing authors
    """
    list = []
    for author in authors:
        last_name = author.lastname.string if author.lastname else ''
        fore_name = author.forename.string if author.forename else ''
        list.append(f'{last_name}, {fore_name}')
    return list

def pubmed_get_date(date):
    """
    Converts XML date element into datetime object
    :param date: date element containing year, month, and date elements
    """
    if not date:
        return None
    return datetime.datetime(int(date.year.string), int(date.month.string), int(date.day.string))

def pubmed_get_string(element):
    """
    Returns string of XML element if element exists
    :param element: XML element
    """
    return element.string if element else None

def pubmed_scraper(collection_name, classifier, term = ''):
    """
    Scrapes metadata of PubMed articles returned by search term query, processes
    abstracts, and stores relevant articles

    :param collection_name: name of collection to store abstracts and metadata
    :param classifier: classifier model to determine if abstracts are relevant
    :param term: PubMed term query
    """
    print(f'Database: PubMed, Term: {term}')

    uids = []
    page = 0
    total = 100000

    # progress bar
    bar = ChargingBar('Getting UIDs:', max=total, suffix='%(index)d of %(max)d')

    while page < total:
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retstart={page}&retmax=100000'
        response = requests.get(url)

        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')

            # updates total to total number of papers in query
            if page == 0:
                total = int(soup.retmax.string)
                bar.max = total

            # stores UIDs returned by query
            for j, id in enumerate(soup.find_all('id')):
                uids.append(id.string)
                bar.next()

        page += 100000
    bar.finish()

    page = 0

    # gets metadata and abstracts
    articles = []
    abstracts = []
    already_stored = []
    total = len(uids)

    # sets up collection
    collection = DB[collection_name]

    # progress bar
    bar = ChargingBar('Getting metadata:', max=total, suffix='%(index)d of %(max)d')

    while page < total:
        # creates url to query metadata for 200 uids
        sub_uids = ','.join(uids[page:page + 200])
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={sub_uids}&retmode=xml'
        response = requests.get(url)

        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')
            entries = soup.find_all('pubmedarticle')

            # stores UIDs returned by query
            for article in entries:

                # checks if paper is already in database using uid
                uid = pubmed_get_string(article.find('pmid'))
                doi = pubmed_get_string(article.find('elocationid', eidtype='doi'))

                if collection.count_documents({ '$or': [ { 'uid': uid }, { 'doi': doi } ] }, limit = 1):
                    already_stored.append(uid)
                else:
                    # store abstract text for use by mat2vec below
                    abstract = pubmed_remove_html(article.abstracttext)

                    # occasionally papers had no abstract, so skip over those
                    if not abstract:
                        bar.next()
                        continue

                    # processes abstract text using processor from mat2vec
                    tokens, materials = PROCESSOR.process(abstract)
                    processed_abstract = ' '.join(tokens)

                    # converts metadata to json format
                    article = {
                        'doi': pubmed_get_string(article.find('elocationid', eidtype="doi")),
                        'uid': uid,
                        'title': pubmed_remove_html(article.articletitle),
                        'abstract': abstract,
                        'creators': pubmed_get_authors(article.find_all('author')),
                        'publication_name': pubmed_remove_html(article.journal.title),
                        'issn': pubmed_get_string(article.find('issn', issntype='Print')),
                        'eissn': pubmed_get_string(article.find('issn', issntype='Electronic')),
                        'publication_date': pubmed_get_date(article.articledate),
                        'database': 'pubmed',
                        'processed_abstract': processed_abstract
                    }
                    articles.append(article)
                    abstracts.append(processed_abstract)
                bar.next()
        page += 200
    bar.finish()

    # already stored
    print(f'\nAlready stored: {len(already_stored)}')
    for uid in already_stored:
        print(f'\t{uid}')

    store(collection, classifier, articles, abstracts)

def store(collection, classifier, articles, abstracts):
    """
    Classifies articles based on processed abstracts and stores in database if
    relevant

    :param collection: MongoDB collection to store abstracts and metadata
    :param classifier: classifier model to determine if abstracts are relevant
    :param articles: list of metadata of abstracts
    :param abstracts: list of processed abstracts to predict on
    """
    # if no abstracts to store, exit
    if len(abstracts) == 0:
        print('No abstracts to store')
        return

    # uses classifier to determine if relevant
    predictions = classifier.predict(abstracts)

    # keeps articles to be stored in database
    relevant = []

    # progress bar
    bar = ChargingBar('Classifying papers:', max = len(abstracts), suffix = '%(index)d of %(max)d')

    # appends articles to be stored in database to relevant list if relevant
    for i, article in enumerate(articles):
        if predictions[i]:
            relevant.append(article)
        bar.next()
    bar.finish()

    # stores abstracts in database
    collection.insert_many(relevant)

    print(f'Relevant abstracts: {len(relevant)}')
    print(f'Irrelevant abstracts: {len(articles) - len(relevant)}')
    print(f'Total: {len(articles)}')
