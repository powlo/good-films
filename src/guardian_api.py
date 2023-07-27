import logging
import re
from datetime import datetime, timedelta

import requests

from aws_utils import get_secret

BASE_URL = "https://content.guardianapis.com"
SEARCH_URL = BASE_URL + "/search"
TITLE_REGEX = re.compile(r"^([\w\s:’]+)\sreview")
YESTERDAY = datetime.now() - timedelta(days=1)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_films(from_date=YESTERDAY):
    params = {
        "api-key": get_secret("GuardianAPI")["API_KEY"],
        "star-rating": "4|5",
        "section": "film",
        "show-fields": ["byline", "starRating"],
        "show-references": "imdb",
        "show-tags": "contributor",
        "from-date": from_date.strftime("%Y-%m-%d"),
    }
    # gets films from guardian.
    response = requests.get(SEARCH_URL, params=params)

    # TODO: What if we don't succeed?
    response = response.json()
    films = response["response"]["results"]
    if films:
        logger.info("Found %s film reviews." % len(films))
    else:
        logger.info("No film reviews found.")
    new_films = []
    for film in films:
        new_film = {}
        match = TITLE_REGEX.match(film["webTitle"])
        if match:
            new_film["title"] = match.group(1)
        else:
            logger.warn("Couldn't figure out what the title was.")
            logger.warn('Here\'s the raw title: "%s"' % film["webTitle"])
        if "references" in film:
            for ref in film["references"]:
                if ref["type"] == "imdb":
                    new_film["imdb"] = ref["id"].split("/")[-1]
        if new_film:
            new_films.append(new_film)
        else:
            logger.warn('Got no useful data from "%s"' % film["webUrl"])
    return new_films
