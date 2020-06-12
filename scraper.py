import requests
import json
import os

SPRINGER_NATURE_API_KEY = os.environ.get('SPRINGER_NATURE_API_KEY')
SPRINGER_NATURE_FIELDS = ['title', 'creators', 'publicationNAME', 'issn',
    'eissn', 'doi', 'publisher', 'publicationDate', 'startingPage', 'endPage',
    'abstract']

def springerUrlBuilder(s, subject, keyword):
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

def springerScraper(subject, keyword):
    """
    Scrapes metadata of all results returned from subject and keyword query
    :param subject: subject constraint query
    :param keyword: keyword constraint query
    """
    i = 1
    total = 100

    while i <= total:
        url = springerUrlBuilder(i, 'Food Science', 'flavor')
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)
            for record in data['records']:
                print('title:', record['title'])
                # print('abstract:', record['abstract'])

            # updates total to total number of papers in query
            if i == 1:
                total = int(data['result'][0]['total'])
        i += 100

def main():
    springerScraper('Food Science', None, SPRINGER_NATURE_API_KEY)

if __name__ == '__main__':
    main()
