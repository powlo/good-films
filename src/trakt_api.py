import json
import os
import logging
import requests


BASE_URL = 'https://api.trakt.tv'
SEARCH_TEXT_URL = BASE_URL + '/search/movie'
SEARCH_IMDB_URL = BASE_URL + '/search/imdb/%s'
LIST_URL = BASE_URL + '/users/%s/lists/%s/items' % ('ukdefresit', 'guardian-films')

CLIENT_ID = os.environ.get('TRAKT_CLIENT_ID')
ACCESS_TOKEN = os.environ.get('TRAKT_ACCESS_TOKEN')

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
            logger.info('Used imdb reference to get trakt id')
            response = requests.get(SEARCH_IMDB_URL % film['imdb'], headers=headers)
            results = response.json()
        else:
            logger.info('No imdb reference provided. Performed text search.')
            params = {'query' : film['title'], 'fields':'title'}
            response = requests.get(SEARCH_TEXT_URL, params=params, headers=headers)
            results = response.json()

        film = results[0]['movie']
        id = film['ids']['trakt']
        trakt_ids.add(id)
        logger.info('Found "%s (%s)", <trakt %s> on trakt.' % (film['title'], film['year'], id))

    # Now turn that list of ids into a POST
    data = {}
    data['movies'] = [{'ids': {'trakt': id}} for id in trakt_ids]
    response = requests.post(LIST_URL, data=json.dumps(data), headers=headers)
    if response.ok:
        logger.info('Successfully added films to trakt list.')
    else:
        logger.error('Failed to add films to trakt list.')
        logger.info('URL: %s' % response.url)
        logger.info('Reason: (%s) %s' % (response.status_code, response.reason))