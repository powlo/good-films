from __future__ import annotations
import logging
import re
from datetime import datetime

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


def get_title(article: dict) -> str:
    webTitle = article["webTitle"]
    title_regex = re.compile(r"^([\w\s\-:,’]+)\sreview")
    match = title_regex.match(webTitle)
    if match:
        return str(match.groups(1)[0])
    else:
        raise ValueError(f'No title found in "${webTitle}"')

def get_url(article: dict) -> str:
    return article["webUrl"]

class Article:
    def __init__(self, title: str, url: str, imdb_id: str | None = None):
        self.title = title
        self.url = url
        self.imdb_id = imdb_id

    @classmethod
    def from_dict(cls, article) -> Article:
        title = get_title(article)
        url = get_url(article)
        imdb_id = get_imdb_id(article)

        return cls(title, url, imdb_id)

    def to_dict(self):
        return dict(title=self.title, url=self.url, imdb_id=self.imdb_id)

def get_articles(from_date: datetime):
    current_page = 1
    pages = 1
    from_date_string = from_date.strftime("%Y-%m-%d")
    while current_page <= pages:
        params = {
            "api-key": get_secret("GuardianAPI")["API_KEY"],
            "star-rating": "4|5",
            "section": "film",
            "show-fields": ["byline", "starRating"],
            "show-references": "imdb",
            "show-tags": "contributor",
            "from-date": from_date_string,
            "page": current_page,
        }
        # gets film reviews from guardian.
        response = requests.get(SEARCH_URL, params=params)
        json_data = response.json()
        pages = json_data["response"]["pages"]
        results = json_data["response"]["results"]
        for data in results:
            try:
                article = Article.from_dict(data)
            except Exception as e:
                # Some sort of parse error occurred.
                logger.error(e)
                continue
            yield article
        current_page += 1
