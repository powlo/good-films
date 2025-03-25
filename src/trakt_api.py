import json
import logging
from typing import Set

import requests

from aws_utils import get_secret

BASE_URL = "https://api.trakt.tv"
SEARCH_TEXT_URL = BASE_URL + "/search/movie"
SEARCH_IMDB_URL = BASE_URL + "/search/imdb/%s"
USER_SETTINGS_URL = BASE_URL + "/users/settings"
LIST_URL = BASE_URL + "/users/%s/lists/%s/items" % ("ukdefresit", "guardian-films")

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
    # TODO: Remove.
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


def post_film_ids(ids: Set[str]):
    """
    Takes a set of ids that can be recognised by IMDB (eg tt0076759)
    and POSTs them to trakt.
    """
    headers = get_headers()
    trakt_ids = set()
    for imdb_id in ids:
        results = search_by_imdb_id(imdb_id)
        try:
            film = results[0]["movie"]
        except IndexError:
            logger.warn("Skipping '%s' because no results were found.", imdb_id)
            continue
        except KeyError:
            logger.warn(
                "Skipping '%s' because results do not contain movie information.",
                imdb_id,
            )
            continue
        track_id = film["ids"]["trakt"]
        trakt_ids.add(track_id)
        logger.info(
            'Found "%s (%s)", <imdb %s> on trakt.'
            % (film["title"], film["year"], imdb_id)
        )

    # Now turn that list of ids into a POST
    data = {}
    data["movies"] = [{"ids": {"trakt": id}} for id in trakt_ids]

    # TODO: We need to handle situation where we're trying to post continuously.
    # response will contain a "retry-after" in the header. User that.
    response = requests.post(LIST_URL, data=json.dumps(data), headers=headers)
    if response.ok:
        logger.info("Successfully added %d films to trakt list." % len(trakt_ids))
    else:
        logger.error("Failed to add films to trakt list.")
        logger.info("URL: %s" % response.url)
        logger.info("Reason: (%s) %s" % (response.status_code, response.reason))


# Mostly for debug purposes.
def get_user_settings():
    headers = get_headers()
    response = requests.get(USER_SETTINGS_URL, headers=headers)
    print(response)
