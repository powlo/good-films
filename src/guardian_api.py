import logging
import re
from datetime import datetime
from typing import List, Set

import requests

from aws_utils import get_secret

BASE_URL = "https://content.guardianapis.com"
SEARCH_URL = BASE_URL + "/search"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Code that interacts with Guardian API.
# Documentation is found here: https://open-platform.theguardian.com/documentation/


def get_imdb_id(article: dict) -> str | None:
    """
    Extracts the imdb ids from a list of films provided by the Guardian API.
    """
    for ref in article.get("references", []):
        if ref["type"] == "imdb":
            id = ref["id"].split("/")[-1]
            return id


def get_title(article: dict) -> str | None:
    webTitle = article.get("webTitle", "")
    title_regex = re.compile(r"^([\w\s\-:,’]+)\sreview")
    match = title_regex.match(webTitle)
    if match:
        return str(match.groups(1)[0])


def get_url(article: dict) -> str | None:
    return article.get("webUrl", None)


def parse(article: dict) -> dict:
    title = get_title(article)
    url = get_url(article)
    imdb_id = get_imdb_id(article)
    return {"title": title, "url": url, "imdb_id": imdb_id}


class GuardianFilm:
    def __init__(self, title: str, url: str, imdb_id: str):
        self.title = title
        self.url = url
        self.imdb_id = imdb_id


def extract_imdb_ids(results: List) -> Set:
    """
    Extracts the imdb ids from a list of films provided by the Guardian API.
    """
    ids = set()
    for result in results:
        if "references" not in result or not result["references"]:
            logger.warning(f'No references for article "{result["webTitle"]}"')
            continue
        for ref in result["references"]:
            if ref["type"] == "imdb":
                id = ref["id"].split("/")[-1]
                ids.add(id)
            else:
                logger.warning(f'No imdb references for article "{result["webTitle"]}"')
    return ids


def get_articles(from_date: datetime):
    current_page = 1
    pages = 1
    while current_page <= pages:
        params = {
            "api-key": get_secret("GuardianAPI")["API_KEY"],
            "star-rating": "4|5",
            "section": "film",
            "show-fields": ["byline", "starRating"],
            "show-references": "imdb",
            "show-tags": "contributor",
            "from-date": from_date.strftime("%Y-%m-%d"),
            "page": current_page,
        }
        # gets film reviews from guardian.
        response = requests.get(SEARCH_URL, params=params)
        data = response.json()
        pages = data["response"]["pages"]
        articles = data["response"]["results"]
        for article in articles:
            yield article
        current_page += 1
