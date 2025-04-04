import logging
import re
from datetime import datetime
from typing import List, Set

import requests

from aws_utils import get_secret

BASE_URL = "https://content.guardianapis.com"
SEARCH_URL = BASE_URL + "/search"
TITLE_REGEX = re.compile(r"^([\w\s\-:,’]+)\sreview")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Code that interacts with Guardian API.
# Documentation is found here: https://open-platform.theguardian.com/documentation/


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


def get_films(from_date: datetime):
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
        # gets films from guardian.
        response = requests.get(SEARCH_URL, params=params)
        data = response.json()
        pages = data["response"]["pages"]
        films = data["response"]["results"]
        yield films
        current_page += 1
