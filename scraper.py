import requests
import json
import os

SPRINGER_NATURE_API_KEY = os.environ.get('SPRINGER_NATURE_API_KEY')
ELSEVIER_API_KEY = os.environ.get('ELSEVIER_API_KEY')
SPRINGER_NATURE_FIELDS = ['title', 'creators', 'publicationName', 'issn', 'doi',
    'publisher', 'publicationDate', 'startingPage', 'endPage', 'abstract']
SCIENCE_DIRECT_FIELDS = ['dc:title', 'dc:creator', 'prism:publicationName',
    'prism:issn', 'prism:doi', 'prism:publisher', 'prism:coverDate',
    'prism:pageRange', 'prism:endingPage', 'dc:description']

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

def springer_scraper(subject = '', keyword = ''):
    """
    Scrapes metadata of all results returned from subject and keyword query
    :param subject: subject constraint query, if empty does not include subject constraint to query
    :param keyword: keyword constraint query, if empty does not include keyword constraint to query
    """
    i = 1
    total = 100

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
                print(f'Getting metadata of paper {i + j}/{total}...')
                print('title:', record['title'])
                # print('abstract:', record['abstract'])

        i += 100

def elsevier_get_dois(url):
    """
    Scrapes dois of all results from url
    :param url: Elsevier API url query
    """
    dois = []
    page = 0

    while page < 1:
        print(f'\tGetting dois from results on page {page + 1}...')
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)['search-results']

            # stores dois
            for entry in data['entry']:
                doi = entry['prism:doi']
                if doi not in dois:
                    dois.append(doi)
                    # print(doi)

            # if current page is last page, break
            if data['link'][0]['@href'] == data['link'][3]['@href']:
                break

            # queries next page in search
            url = data['link'][2]['@href']
        page += 1
    return dois

def elsevier_scraper(query):
    """
    Scrapes metadata of all results of query from Elsevier databases (Scopus
    and Science Direct)
    :param query: Elsevier database query
    """
    scopus_url = f'https://api.elsevier.com/content/search/scopus?query=TITLE-ABS-KEY({query})%20AND%20DOCTYPE(ar)&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
    sd_url = f'https://api.elsevier.com/content/search/sciencedirect?query={query}&apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'

    print(f'Getting dois from Scopus database:')
    scopus_dois = elsevier_get_dois(scopus_url)
    print(f'Getting dois from ScienceDirect database:')
    sd_dois = elsevier_get_dois(sd_url)

    # gets metadata for ScienceDirect articles
    print(f'Getting metadata from ScienceDirect papers:')
    for i, doi in enumerate(sd_dois):
        print(f'\Getting metadata of paper {i + 1}/{len(sd_dois)}...')
        url = f'https://api.elsevier.com/content/article/doi/{doi}?apiKey={ELSEVIER_API_KEY}&httpAccept=application%2Fjson'
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)['full-text-retrieval-response']['coredata']
            print('title:', data['dc:title'])
            # print(data['dc:description'])

def main():
    springer_scraper(subject='Food Science', keyword='flavor compounds')
    elsevier_scraper('flavor compounds')

if __name__ == '__main__':
    main()
