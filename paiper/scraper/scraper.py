from pymongo import MongoClient
from bs4 import BeautifulSoup
from paiper.processor import MaterialsTextProcessor
from paiper.classifier import Classifier
import requests
import json
import re
import datetime
import os

SPRINGER_NATURE_API_KEY = os.environ.get('SPRINGER_NATURE_API_KEY', 'Springer key doesn\'t exist')
ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY', 'Elsevier key doesn\'t exist')
SCIENCE_DIRECT_FIELDS = ['dc:title', 'dc:creator', 'prism:publicationName',
    'prism:issn', 'prism:doi', 'prism:publisher', 'prism:coverDate',
    'prism:pageRange', 'prism:endingPage', 'dc:description']
PUBMED_FIELDS = ['articletitle', 'author', 'title', 'issn', 'elocationid',
    'pubdate', 'abstracttext']

PROCESSOR = MaterialsTextProcessor()

DATABASE_URL = os.environ.get('DATABASE_URL', 'Database url doesn\'t exist')

CLIENT = MongoClient(DATABASE_URL)
DB = CLIENT.papers
COLL = DB.sample

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
    if urls:
        for url in urls:
            if url['format'] == '':
                return url['value']
        return urls[0]['value']
    else:
        return None

def springer_get_date(date):
    """
    Converts date into datetime object
    :param date: date formatted 'YYYY-MM-DD'
    """
    date_array = date.split('-')
    return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

def springer_scraper(subject = '', keyword = ''):
    """
    Scrapes metadata of Springer Nature articles returned by subject and
    keyword query
    :param subject: subject constraint query, if empty does not include subject
    constraint to query
    :param keyword: keyword constraint query, if empty does not include keyword
    constraint to query
    """
    i = 1
    total = 100

    print(f'Getting metadata of Springer Nature papers:')
    while i <= total:
        url = springer_url_builder(i, subject, keyword)
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)

            # updates total to total number of papers in query
            if i == 1:
                total = int(data['result'][0]['total'])

            # gets metadata
            for j, record in enumerate(data['records']):
                print(f'\tStoring metadata of paper {i + j}/{total}...')

                # checks if paper is already in database using doi
                doi = record['doi']
                if COLL.count_documents({ 'doi': doi }, limit = 1):
                    print(f'\tThis paper is already stored: {doi}')
                else:
                    # processes abstract text using processor from mat2vec
                    tokens, materials = PROCESSOR.process(record['abstract'])

                    # TODO: apply binary classifier to determine if relevant or not
                    processed_abstract = ' '.join(tokens)

                    # stores paper and metadata in database
                    paper = {
                        'doi': doi,
                        'title': record['title'],
                        'abstract': record['abstract'],
                        'url': springer_get_url(record['url']),
                        'creators': springer_get_creators(record['creators']),
                        'publication_name': record['publicationName'],
                        'issn': record['issn'],
                        'eissn': record['eIssn'],
                        'publication_date': springer_get_date(record['publicationDate']),
                        'start_page': int(record['startingPage']),
                        'end_page': int(record['endingPage']),
                        'database': 'springer',
                        'processed_abstract': processed_abstract
                    }
                    COLL.insert_one(paper)

        i += 100

def elsevier_get_dois(url):
    """
    Scrapes dois of all results from url
    :param url: Elsevier API url query
    """
    dois = []
    page = 0

    while page < 4:
        print(f'\tGetting dois from results on page {page + 1}...')

        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)['search-results']

            # stores dois
            for entry in data['entry']:
                dois.append(entry['prism:doi'])

            # if current page is last page, break
            if data['link'][0]['@href'] == data['link'][3]['@href']:
                break

            # sets url to next page in search
            url = data['link'][-2]['@href']
        page += 1
    return dois

def sd_get_date(date): # could potentially combine this with springer_get_date() since code is identical
    """
    Converts date into datetime object
    :param date: date formatted 'YYYY-MM-DD'
    """
    date_array = date.split('-')
    return datetime.datetime(int(date_array[0]), int(date_array[1]), int(date_array[2]))

def sd_get_creators(creators):
    """
    Turns list of dictionary of creators into list of creators and ignores extraneous data
    :param creators: list of creators where each creator is inside a dictionary
    """
    list = []
    for entry in creators:
        list.append(entry['$'])
    return list

def sd_get_page(query, info):
    """
    Some articles have starting-page/ending-page and others don't, so attempts to return page if present
    If the field does not exist, returns a blank string
    :param query: index within the json file where ending page is located (if it exists)
    :param info: json file
    """
    try:
        page = info[query]
        return int(page)
    except KeyError:
        return ''

def elsevier_scraper(query):
    """
    Scrapes metadata of Elsevier (Scopus and ScienceDirect) articles returned
    by query
    :param query: Elsevier database query
    """
    # creates search urls
    scopus_url = f'https://api.elsevier.com/content/search/scopus?query=TITLE-ABS-KEY({query})%20AND%20DOCTYPE(ar)&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
    sd_url = f'https://api.elsevier.com/content/search/sciencedirect?query={query}&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'

    # gets dois
    # print(f'Getting dois from Scopus database:')
    # scopus_dois = elsevier_get_dois(scopus_url)
    print(f'Getting dois from ScienceDirect database:')
    sd_dois = elsevier_get_dois(sd_url)

    # TODO: get metadata for Scopus articles (doesn't return abstract for some reason, contacted API support)

    # gets metadata for ScienceDirect articles
    print(f'Getting metadata of ScienceDirect papers:')
    for i, doi in enumerate(sd_dois):
        print(f'\tGetting and storing metadata of paper {i + 1}/{len(sd_dois)}...')

        url = f'https://api.elsevier.com/content/article/doi/{doi}?apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)['full-text-retrieval-response']['coredata']
            # print('\ttitle:', data['dc:title'])

            # checks if paper is already in database using doi
            if COLL.count_documents({ 'doi': doi }, limit = 1):
                print(f'\tThis paper is already stored: {doi}')
            else:
                # processes abstract text using processor from mat2vec
                tokens, materials = PROCESSOR.process(data['dc:description'])

                # TODO: apply binary classifier to determine if relevant or not
                processed_abstract = ' '.join(tokens)

                # stores paper and metadata in database
                paper = {
                        'doi': doi,
                        'title': data['dc:title'],
                        'abstract': data['dc:description'],
                        'url': data['prism:url'],
                        'creators': sd_get_creators(data['dc:creator']),
                        'publication_name': data['prism:publicationName'],
                        'issn': data['prism:issn'],
                        'publication_date': sd_get_date(data['prism:coverDate']),
                        'start_page': sd_get_page('prism:startingPage', data),
                        'end_page': sd_get_page('prism:endingPage', data),
                        'database': 'ScienceDirect',
                        'processed_abstract': processed_abstract
                    }
                COLL.insert_one(paper)

def pubmed_remove_html(element):
    """
    Removes HTML formatting from contents of field
    :param element: HTML/XML element of field
    """
    if not element:
        return None
    string = ''
    for content in element.contents:
        string += re.sub('\s*\<[^)]*\>', '', str(content)) # @bianca should there be an r before the string? TODO: resolve the warning
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

def pubmed_scraper(term):
    """
    Scrapes metadata of PubMed articles returned by search term query
    :param term: PubMed term query
    """
    uids = []

    i = 0
    total = 100000

    # getting uids
    print(f'Getting UIDs of PubMed papers...')
    while i < total:
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retstart={i}&retmax=100000'
        response = requests.get(url)
        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')

            # updates total to total number of papers in query
            if i == 0:
                total = int(soup.retmax.string)

            # stores UIDs returned by query
            for j, id in enumerate(soup.find_all('id')):
                uids.append(id.string)

        i += 100000

    i = 0

    # getting metadata
    print(f'Getting metadata of PubMed papers:')
    while i < 200:
        # creates url to query metadata for for 200 uids
        sub_uids = ','.join(uids[i:i + 200])
        url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={sub_uids}&retmode=xml'
        response = requests.get(url)
        if response.ok:
            soup = BeautifulSoup(response.content, 'html.parser')

            # stores UIDs returned by query
            for j, article in enumerate(soup.find_all('pubmedarticle')):
                print(f'\tGetting and storing metadata of papers {i + j + 1}/{total}...')

                # checks if paper is already in database using doi
                doi = str(article.find('elocationid', eidtype='doi').string)
                if COLL.count_documents({ 'doi': doi }, limit = 1):
                    print(f'\tThis paper is already stored: {doi}')
                else:
                    # store abstract text for use by mat2vec below
                    abstract = pubmed_remove_html(article.abstracttext)

                    # occasionally papers had no abstract, so skip over those
                    if abstract == None:
                        print(f'\tThis paper: {doi} has an empty abstract. Skipping...')
                        continue
                    tokens, materials = PROCESSOR.process(abstract)
                    
                    # TODO: apply binary classifier to determine if relevant or not
                    processed_abstract = ' '.join(tokens)

                    # stores paper and metadata in database
                    paper = {
                        'doi': doi,
                        'title': pubmed_remove_html(article.articletitle),
                        'abstract': abstract, # see above
                        'creators': pubmed_get_authors(article.find_all('author')),
                        'publication_name': pubmed_remove_html(article.journal.title),
                        'issn': pubmed_get_string(article.find('issn', issntype='Print')),
                        'eissn': pubmed_get_string(article.find('issn', issntype='Electronic')),
                        'publication_date': pubmed_get_date(article.articledate),
                        'database': 'pubmed',
                        'processed_abstract': processed_abstract
                    }
                    COLL.insert_one(paper)

        i += 200

def main():
    
    # springer_scraper(subject='Food Science', keyword='flavor compounds')
    # elsevier_scraper('flavor compounds')
    # pubmed_scraper('flavor compounds')

if __name__ == '__main__':
    main()
