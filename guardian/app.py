import json
import logging
import os
from datetime import datetime
from typing import Iterator

import boto3
import requests
from aws_utils import get_parameter, get_secret, put_parameter

BASE_URL = "https://content.guardianapis.com"
SEARCH_URL = BASE_URL + "/search"
GUARDIAN_ARTICLE_QUEUE_URL = os.environ["GUARDIAN_ARTICLE_QUEUE_URL"]
DATE_FORMAT = "%Y-%m-%d"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")


def get_articles(from_date: datetime) -> Iterator[dict]:
    current_page = 1
    pages = 1
    from_date_string = from_date.strftime("%Y-%m-%d")
    logger.info(f"Fetching articles from {from_date_string}")
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
        # gets raw articles from guardian.
        logger.info(f"Fetching page {current_page} of results.")
        response = requests.get(SEARCH_URL, params=params)
        json_data = response.json()
        pages = json_data["response"]["pages"]
        results = json_data["response"]["results"]
        logger.info(f"Got {len(results)} results from {SEARCH_URL}.")
        for data in results:
            yield data
        current_page += 1


def lambda_handler(event=None, context=None):
    # The date the last time the script successfully ran is stored in a parameter.
    # So days are not lost if the script fails for any reason.
    last_success = get_parameter("GoodFilms_LastSuccess")
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        last_success = input(f"From Date ({last_success}): ")
    from_date = datetime.strptime(last_success, DATE_FORMAT)

    for data in get_articles(from_date):
        sqs.send_message(
            QueueUrl=GUARDIAN_ARTICLE_QUEUE_URL, MessageBody=json.dumps(data)
        )
    now = datetime.now()
    put_parameter("GoodFilms_LastSuccess", now.strftime(DATE_FORMAT))


if __name__ == "__main__":
    lambda_handler()
