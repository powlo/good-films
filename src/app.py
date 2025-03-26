import logging
import sys
from datetime import datetime

import guardian_api
import trakt_api
from aws_utils import get_parameter, put_parameter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    # The date the last time the script ran is stored in a parameter.
    # So days are not lost if the script fails for any reason.
    last_success = get_parameter("GoodFilms_LastSuccess")
    from_date = datetime.strptime(last_success, "%Y-%m-%d")

    for films in guardian_api.get_films(from_date):
        if films:
            logger.info("Found %s film reviews." % len(films))
            for film in films:
                logger.info(f'"{film["webTitle"]}" ({film["webUrl"]})')
            imdb_ids = guardian_api.extract_imdb_ids(films)
            trakt_api.update_list(imdb_ids)
        else:
            logger.info("No film reviews found.")

    # Update the "LastSuccess" parameter ready for the next run.
    now = datetime.now()
    put_parameter("GoodFilms_LastSuccess", now.strftime("%Y-%m-%d"))


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    lambda_handler(None, None)
