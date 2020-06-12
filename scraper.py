import requests
import json
import os

def springerUrlBuilder(s, subject, keyword, api):
    # builds query
    query = 'type:Journal'
    if subject:
        query += f'+subject:\"{subject}\"'
    if keyword:
        query += f'+keyword:\"{keyword}\"'

    # builds url
    return f'http://api.springernature.com/meta/v2/json?s={s}&p=100&q=({query})&api_key={api}'

def springerScraper(subject, keyword, api):
    i = 1
    total = 100

    while i <= total:
        url = springerUrlBuilder(i, 'Food Science', 'flavor', api)
        response = requests.get(url)
        if response.ok:
            data = json.loads(response.content)
            for record in data['records']:
                print('title:', record['title'])
                print('abstract:', record['abstract'])

            # updates total to total number of papers in query
            if i == 1:
                total = int(data['result'][0]['total'])
        i += 100

def main():
    api = os.environ.get('SPRINGER_NATURE_API_KEY')
    springerScraper('Food Science', 'flavor', api)

if __name__ == '__main__':
    main()
