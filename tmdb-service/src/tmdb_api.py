import logging
from urllib.parse import urljoin

import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class TmdbAPI:
    def __init__(
        self,
        read_access_token: str,
        username: str,
        password: str,
        base_url="https://api.themoviedb.org/3/",
    ):
        self.base_url = base_url
        headers = {
            "Authorization": f"Bearer {read_access_token}",
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        # Get a request token using the access token
        url = urljoin(base_url, "authentication/token/new")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        request_token = response.json()["request_token"]

        # Validate the request token using username/password
        url = urljoin(base_url, "authentication/token/validate_with_login")
        data = {
            "username": username,
            "password": password,
            "request_token": request_token,
        }
        response = requests.post(url, headers=headers, json=data)

        # Now create a session id with the "validated" request token.
        url = urljoin(base_url, "authentication/session/new")
        data = {"request_token": request_token}
        response = requests.post(url, headers=headers, json=data)
        self.session_id = response.json()["session_id"]
        self.headers = headers

    def search(self, query: str, page=1):
        response = requests.get(
            urljoin(self.base_url, f"search/movie?query={query}&page={page}"),
            headers=self.headers,
        )
        return response.json()

    def add(self, movie_id: int, list_id: int):
        data = {"media_id": movie_id}
        headers = self.headers
        response = requests.post(
            urljoin(self.base_url, f"list/{list_id}/add_item"),
            headers=headers,
            json=data,
            params={"session_id": self.session_id},
        )
        return response.json()
