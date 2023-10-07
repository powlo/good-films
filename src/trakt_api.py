import json
import logging
import os

import requests

from aws_utils import get_secret

BASE_URL = "https://api.trakt.tv"
SEARCH_TEXT_URL = BASE_URL + "/search/movie"
SEARCH_IMDB_URL = BASE_URL + "/search/imdb/%s"
LIST_URL = BASE_URL + "/users/%s/lists/%s/items" % ("ukdefresit", "guardian-films")

CLIENT_ID = os.environ.get("TRAKT_CLIENT_ID")
ACCESS_TOKEN = os.environ.get("TRAKT_ACCESS_TOKEN")


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_headers():
    secrets = get_secret("TraktAPI")
    return {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "Authorization": f"Bearer {secrets['ACCESS_TOKEN']}",
        "trakt-api-key": secrets["CLIENT_ID"],
    }


def search_by_exact_title(title):
    """
    Convenience wrapper around trakt api to search by exact title matches.
    """
    # NB We put the film title in double quotes to perform an exact match.
    params = {"query": '"%s"' % title, "fields": "title"}
    headers = get_headers()
    return requests.get(SEARCH_TEXT_URL, params=params, headers=headers).json()


def search_by_imdb_id(id):
    """
    Convenience wrapper around trakt api to search by imdb id .
    """
    headers = get_headers()
    return requests.get(SEARCH_IMDB_URL % id, headers=headers).json()


def post_films(films):
    headers = get_headers()
    trakt_ids = set()
    for film in films:
        if film.get("imdb"):
            logger.info("Used imdb reference to get trakt id")
            results = search_by_imdb_id(film["imdb"])
        else:
            logger.info("No imdb reference provided. Performed text search.")
            results = search_by_exact_title(film["title"])

        try:
            film = results[0]["movie"]
        except IndexError:
            logger.warn("Skipping '%s' because no results were found.", film["title"])
            continue
        except KeyError:
            logger.warn(
                "Skipping '%s' because results do not contain movie information.",
                film["title"],
            )
            continue
        id = film["ids"]["trakt"]
        trakt_ids.add(id)
        logger.info(
            'Found "%s (%s)", <trakt %s> on trakt.' % (film["title"], film["year"], id)
        )

    # Now turn that list of ids into a POST
    data = {}
    data["movies"] = [{"ids": {"trakt": id}} for id in trakt_ids]
    response = requests.post(LIST_URL, data=json.dumps(data), headers=headers)
    if response.ok:
        logger.info("Successfully added %d films to trakt list." % len(trakt_ids))
    else:
        logger.error("Failed to add films to trakt list.")
        logger.info("URL: %s" % response.url)
        logger.info("Reason: (%s) %s" % (response.status_code, response.reason))
