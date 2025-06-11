import json
import logging
from typing import List

import requests

from aws_utils import get_secret

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ListRoute:
    def __init__(
        self, session: requests.Session, base_url: str, user_id: str, list_id: str
    ):
        self.session = session
        # user_id is the username of the person who owns the list.
        self.user_id = user_id
        # list_id is the name of the list.
        self.list_id = list_id
        self.base_url = base_url + f"/users/{user_id}/lists/{list_id}/items"

    def get(self, category="movies", sort_by="added", sort_order="desc"):
        url = self.base_url + f"/{category}/{sort_by}/{sort_order}"
        response = self.session.get(url)
        # Raise exception if no bueno.
        response.raise_for_status()
        return response.json()

    def add(self, imdb_ids: List[str]) -> dict:
        data = {"movies": [{"ids": {"imdb": imdb_id}} for imdb_id in imdb_ids]}

        # TODO: We need to handle situation where we're trying to post continuously.
        # response will contain a "retry-after" in the header. Maybe use that.
        response = self.session.post(self.base_url, data=json.dumps(data))
        response.raise_for_status()
        return response.json()

    def delete(self, imdb_ids: List[str]) -> dict:
        url = self.base_url + "/remove"
        data = {"movies": [{"ids": {"imdb": imdb_id}} for imdb_id in imdb_ids]}
        response = self.session.post(url, data=json.dumps(data))
        response.raise_for_status()
        return response.json()


class SearchRoute:
    def __init__(self, session: requests.Session, base_url: str):
        self.session = session
        self.base_url = base_url + "/search"

    def by_text(self, text: str, fields="title"):
        url = self.base_url + "/movie"
        params = {"query": '"%s"' % text, "fields": fields}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def by_id(self, id: str, id_type="imdb", type="movie"):
        url = self.base_url + f"/{id_type}/{id}?type={type}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


class MovieRoute:
    def __init__(self, session: requests.Session, base_url: str, movie_id: str):
        self.session = session
        self.base_url = base_url + f"/movies/{movie_id}"

    def aliases(self):
        url = self.base_url + "/aliases"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()


class TraktAPI:
    def __init__(
        self, client_id: str, access_token: str, base_url="https://api.trakt.tv"
    ):
        session = requests.Session()
        session.headers.update(
            {
                "Content-Type": "application/json",
                "trakt-api-version": "2",
                "Authorization": f"Bearer {access_token}",
                "trakt-api-key": client_id,
            }
        )
        self.session = session
        self.base_url = base_url

    def list(self, user_id: str, list_id: str):
        return ListRoute(self.session, self.base_url, user_id, list_id)

    @property
    def search(self):
        return SearchRoute(self.session, self.base_url)

    def movie(self, movie_id: str):
        return MovieRoute(self.session, self.base_url, movie_id)


def update_list(imdb_ids: List[str]):
    """
    Takes a set of ids that can be recognised by IMDB (eg tt0076759)
    and POSTs them to trakt.
    """
    # Observation: We're doing _two_ things at once here. Updating a
    # list (which is nice) and managing the state of the list
    # We should figure out how to split this apart.
    secrets = get_secret("TraktAPI")
    user_id = secrets["USER_ID"]
    list_id = secrets["LIST_ID"]
    max_list_size = int(secrets["MAX_LIST_SIZE"])
    api = TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])
    api_list = api.list(user_id, list_id)
    list_items = api_list.get()
    excess = max(len(list_items) + len(imdb_ids) - max_list_size, 0)
    if excess:
        logger.warning(
            "Too many items in the list. List will be truncated to make room."
        )
        items_to_delete = list_items[:excess]
        imdb_ids_to_delete = [item["movie"]["ids"]["imdb"] for item in items_to_delete]
        response = api_list.delete(imdb_ids_to_delete)
        logger.info("Deleted %s from list." % response["deleted"]["movies"])
        logger.info("List now contains %s items." % response["list"]["item_count"])

    try:
        result = api_list.add(imdb_ids)
        logger.info(
            "Successfully added %d films to trakt list." % result["added"]["movies"]
        )
    except requests.exceptions.JSONDecodeError:
        # We probably want to handle this better.
        # Ie catch when the request fails and (re)raise something appropriate.
        logger.error("Failed to add films to trakt list.")
