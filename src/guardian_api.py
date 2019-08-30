from datetime import datetime, timedelta
import os
import re
import requests

BASE_URL = 'https://content.guardianapis.com'
SEARCH_URL = BASE_URL + '/search'
API_KEY = os.environ.get('GUARDIAN_API_KEY')
TITLE_REGEX = re.compile(r'^([\w\s]+)\sreview')
YESTERDAY = (datetime.now() - timedelta(days=1))

def get_films(from_date=YESTERDAY):
    params = {
        'api-key': API_KEY,
        'star-rating': '4|5',
        'section': 'film',
        'show-fields': ['byline', 'starRating'],
        'show-references': 'imdb',
        'show-tags': 'contributor',
        'from-date': from_date.strftime('%Y-%m-%d')
    }
    # gets films from guardian.
    response = requests.get(SEARCH_URL, params=params)

    # TODO: What if we don't succeed?
    response = response.json()
    films = response['response']['results']

    new_films = []
    for film in films:
        new_film = {}
        match = TITLE_REGEX.match(film['webTitle'])
        if match:
            new_film['title'] = match.group(1)
        if 'references' in film:
            for ref in film['references']:
                if ref['type'] == 'imdb':
                    new_film['imdb'] = ref['id'].split('/')[-1]
        if new_film:
            new_films.append(new_film)
    return new_films
