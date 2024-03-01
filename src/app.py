import logging
from datetime import datetime, timedelta

import guardian_api
import trakt_api

logger = logging.getLogger()
logger.setLevel(logging.INFO)

YESTERDAY = datetime.now() - timedelta(days=1)


def lambda_handler(event, context):
    for films in guardian_api.get_films(YESTERDAY):
        if films:
            logger.info("Found %s film reviews." % len(films))
            for film in films:
                logger.info(f'"{film["webTitle"]}" (f{film["webUrl"]})')
            ids = guardian_api.extract_imdb_ids(films)
        else:
            logger.info("No film reviews found.")
            ids = set()

        trakt_api.post_film_ids(ids)


if __name__ == "__main__":
    lambda_handler(None, None)
