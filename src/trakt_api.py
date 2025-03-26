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
MAX_LIST_SIZE = 100

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
    # TODO: Remove? Seems we can add and delete films directly using imdb id.
    headers = get_headers()
    return requests.get(SEARCH_IMDB_URL % id, headers=headers).json()


def list_get(category="movies", sort_by="added", sort_order="asc"):
    headers = get_headers()
    # NB the documented technique of adding "X-Sort-By" headers does not seem to work.
    # So we do it as part of the url.
    LIST_GET_URL = LIST_URL + f"/{category}/{sort_by}/{sort_order}"
    return requests.get(LIST_GET_URL, headers=headers)


def list_delete(imdb_ids):
    headers = get_headers()
    LIST_DELETE_URL = LIST_URL + "/remove"
    data = {"movies": [{"ids": {"imdb": imdb_id}} for imdb_id in imdb_ids]}
    return requests.post(LIST_DELETE_URL, data=json.dumps(data), headers=headers)


def list_add(imdb_ids):
    headers = get_headers()
    data = {"movies": [{"ids": {"imdb": imdb_id}} for imdb_id in imdb_ids]}

    # TODO: We need to handle situation where we're trying to post continuously.
    # response will contain a "retry-after" in the header. Maybe use that.
    return requests.post(LIST_URL, data=json.dumps(data), headers=headers)


def update_list(imdb_ids: Set[str]):
    """
    Takes a set of ids that can be recognised by IMDB (eg tt0076759)
    and POSTs them to trakt.
    """

    response = list_get(sort_by="added", sort_order="desc")
    list_items = response.json()
    excess = max(len(list_items) + len(imdb_ids) - MAX_LIST_SIZE, 0)
    if excess:
        logger.warning(
            "Too many items in the list. List will be truncated to make room."
        )
        items_to_delete = list_items[:excess]
        imdb_ids_to_delete = set(
            [item["movie"]["ids"]["imdb"] for item in items_to_delete]
        )
        response = list_delete(imdb_ids_to_delete)
        info = response.json()
        logger.info("Deleted %s from list." % info["deleted"]["movies"])
        logger.info("List now contains %s items." % info["list"]["item_count"])

    response = list_add(imdb_ids)
    if response.ok:
        logger.info("Successfully added %d films to trakt list." % len(imdb_ids))
    else:
        logger.error("Failed to add films to trakt list.")
        logger.info("URL: %s" % response.url)
        logger.info("Reason: (%s) %s" % (response.status_code, response.reason))


# Mostly for debug purposes.
def get_user_settings():
    headers = get_headers()
    response = requests.get(USER_SETTINGS_URL, headers=headers)
    print(response)
