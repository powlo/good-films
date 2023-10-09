import logging
import re
from datetime import datetime, timedelta

import requests

from aws_utils import get_secret

BASE_URL = "https://content.guardianapis.com"
SEARCH_URL = BASE_URL + "/search"
TITLE_REGEX = re.compile(r"^([\w\s\-:,’]+)\sreview")
YESTERDAY = datetime.now() - timedelta(days=1)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_results(results):
    """
    Extracts the films from a search response.
    """
    films = []
    if results:
        logger.info("Found %s film reviews." % len(results))
    else:
        logger.info("No film reviews found.")
    for result in results:
        film = {}
        match = TITLE_REGEX.match(result["webTitle"])
        if match:
            film["title"] = match.group(1)
        else:
            logger.warn("Couldn't figure out what the title was.")
            logger.warn('Here\'s the raw title: "%s"' % result["webTitle"])
        if "references" in result:
            for ref in result["references"]:
                if ref["type"] == "imdb":
                    film["imdb"] = ref["id"].split("/")[-1]
        if film:
            logger.info("Review link for '%s': %s", film["title"], result["webUrl"])
            films.append(film)
        else:
            logger.warn('Got no useful data from "%s"' % result["webUrl"])
    return films


def get_films(from_date=YESTERDAY):
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

        # TODO: What if we don't succeed?
        response = response.json()
        pages = response["response"]["pages"]
        results = response["response"]["results"]
        films = parse_results(results)
        yield films
        current_page += 1
