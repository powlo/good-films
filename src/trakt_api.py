import json
import os
import logging
import requests


BASE_URL = 'https://api.trakt.tv'
SEARCH_TEXT_URL = BASE_URL + '/search/movie'
SEARCH_IMDB_URL = BASE_URL + '/search/imdb/%s'
LIST_URL = BASE_URL + '/users/%s/lists/%s/items' % ('ukdefresit', 'guardian-films')

CLIENT_ID = os.environ['TRAKT_CLIENT_ID'] 
ACCESS_TOKEN = os.environ['TRAKT_ACCESS_TOKEN'] 

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def post_films(films):

    headers = {
        "Content-Type": 'application/json',
        "trakt-api-version": '2',
        'Authorization': 'Bearer %s' % ACCESS_TOKEN,
        "trakt-api-key": CLIENT_ID
    }

    trakt_ids = set()
    for film in films:
        if film.get('imdb'):
            logger.info('Using imdb reference to get trakt id')
            response = requests.get(SEARCH_IMDB_URL % film['imdb'], headers=headers)
        else:
            logger.info('No imdb reference provided. Using text search.')
            params = {'query' : film['title'], 'fields':'title'}
            response = requests.get(SEARCH_TEXT_URL, params=params, headers=headers)

        # Filter out non-exact matches.
        results = [x for x in response.json() if x['score'] == 1000]

        # sort by release date, assuming that the review is for the latest film with that title.
        # The slug contains the release date, eg 'the-nightingale-2019-01-25' and appears more
        # more likely to exist than ['movie']['year'].
        results = sorted(results, key=lambda k: k['movie']['ids']['slug'], reverse=True)
        trakt_id = results[0]['movie']['ids']['trakt']
        trakt_ids.add(trakt_id)

    # Now turn that list of ids into a POST
    data = {}
    data['movies'] = [{'ids': {'trakt': id}} for id in trakt_ids]
    response = requests.post(LIST_URL, data=json.dumps(data), headers=headers)
