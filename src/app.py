import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime

import boto3
import inquirer

import guardian_api
import trakt_api
from aws_utils import get_parameter, get_secret, put_parameter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")

MANUAL_PROCESSING_QUEUE_URL = os.environ["MANUAL_PROCESSING_QUEUE_URL"]


@dataclass
class FilmReview:
    title: str
    url: str
    imdb_id: str


def lambda_handler(event, context):
    # The date the last time the script ran is stored in a parameter.
    # So days are not lost if the script fails for any reason.
    last_success = get_parameter("GoodFilms_LastSuccess")
    if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        last_success = input(f"From Date ({last_success}): ")
    from_date = datetime.strptime(last_success, "%Y-%m-%d")

    films = []
    for article in guardian_api.get_articles(from_date):
        logger.info(f'"{article["webTitle"]}" ({article["webUrl"]})')
        film = guardian_api.parse(article)
        films.append(film)

    imdb_ids = [f["imdb_id"] for f in films if f["imdb_id"]]

    films_no_id = [f for f in films if not f["imdb_id"]]
    for film in films_no_id:
        logger.warning(f'No imdb id found for "{film["title"]}"')
        sqs.send_message(
            QueueUrl=MANUAL_PROCESSING_QUEUE_URL, MessageBody=json.dumps(film)
        )
    trakt_api.update_list(imdb_ids)

    # Update the "LastSuccess" parameter ready for the next run.
    now = datetime.now()
    put_parameter("GoodFilms_LastSuccess", now.strftime("%Y-%m-%d"))


def manual_review():
    # To be run by a human to review entries on an SQS queue.
    secrets = get_secret("TraktAPI")
    trakt = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])
    user_id = secrets["USER_ID"]
    list_id = secrets["LIST_ID"]
    api_list = trakt.list(user_id, list_id)

    while True:
        response = sqs.receive_message(QueueUrl=MANUAL_PROCESSING_QUEUE_URL)
        if not response.get("Messages"):
            logger.info("No more films to process.")
            break
        for msg in response["Messages"]:
            data = json.loads(msg["Body"])
            try:
                film = FilmReview(**data)
            except TypeError:
                logger.warning(f"Couldn't extract film review from {data}")
                film = None
            if film:
                imdb_id = prompt_best_match(film.title, film.url)
                if imdb_id:
                    api_list.add([imdb_id])
            sqs.delete_message(
                QueueUrl=MANUAL_PROCESSING_QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"]
            )


def prompt_best_match(title: str, url: str) -> str | None:
    # Interactive function that takes a film title, searches trakt and
    # prompts the user for best match.

    secrets = get_secret("TraktAPI")
    trakt = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])
    results = trakt.search.by_text(title)

    print(f"\nSelect best match for '{title}'")
    print(f"{url}")

    choices_hints = {}
    for result in results:
        if not result["movie"]["ids"]["imdb"]:
            # If there's no imdb then it's probably a low quality entry.
            continue
        year = result["movie"]["year"] or "Unknown Year"
        title = result["movie"]["title"]
        score = int(result["score"])
        imdb_id = result["movie"]["ids"]["imdb"]
        choice = (f"{title} ({year}) [score: {score}]", imdb_id)
        hint = f"https://www.imdb.com/title/{imdb_id}/"
        choices_hints[choice] = hint

    if not choices_hints:
        return
    choices_hints[("[ Skip ]", None)] = None
    questions = [
        inquirer.List(
            "imdb_id",
            message="Select matching film:",
            choices=choices_hints.keys(),
            hints=choices_hints,
        ),
    ]
    answer = inquirer.prompt(questions)
    if answer:
        return answer["imdb_id"]


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    manual_review()
