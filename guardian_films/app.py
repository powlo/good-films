
import json
import os
import requests
import re

GUARDIAN_API_KEY = os.environ['GUARDIAN_API_KEY']
GUARDIAN_BASE_URL = 'https://content.guardianapis.com/search'
GUARDIAN_QUERY_PARAMS = {
    'api-key': GUARDIAN_API_KEY,
    'star-rating': '4|5',
    'section': 'film',
    'show-fields': ['byline', 'starRating'],
    'show-refrences': 'imdb',
    'show-tags': 'contributor',
    'from-date': '2019-08-12'
}

TRAKT_API_KEY = os.environ['TRAKT_API_KEY']

TITLE_REGEX = re.compile(r'^([\w\s]+)\sreview')

def get_guardian_films():
    # gets films from guardian.
    response = requests.get(GUARDIAN_BASE_URL, params=GUARDIAN_QUERY_PARAMS)

    print(response.request.url)
    # What if we don't succeed?
    response = response.json()
    films = response['response']['results']

    new_films = []
    for film in films:
        new_film = {}
        match = TITLE_REGEX.match(film['webTitle'])
        if match:
            new_film['title'] = match.group(1))
        for ref in film['references']:
            if ref['type'] == 'imdb':
                new_film['imdb'] = ref['id']
        new_films.append(new_film)
    return new_films


def post_films():
    # posts films to trakt.
    pass

def lambda_handler(event, context):
    films = get_films()

    # Now do trakt stuff


    # Find the film in trakt
    # if it's found, add it to the list.... ur here
    TRAKT_BASE_URL = 'api.trakt.tv'

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "hello world",
            # "location": ip.text.replace("\n", "")
        }),
    }
