# The code used to manually process a queue.
# Fix this. 23 3 2026
import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from functools import cache

import boto3
import inquirer
import trakt_api

DLQ_URL = os.environ["DLQ_URL"]

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__file__)
sqs = boto3.client("sqs")


@dataclass
class Article:
    web_title: str
    web_url: str

    @property
    def film_title(self) -> str:
        seperator = " review \u2013 "  # u2013 is an n-dash
        return self.web_title.split(seperator)[0]


@cache
def get_secret(secret_id):
    """
    Helper function to get the contents of a given secret.
    """
    session = boto3.Session()
    client = session.client(service_name="secretsmanager", region_name="eu-west-2")
    response = client.get_secret_value(SecretId=secret_id)
    return json.loads(response["SecretString"])


def get_articles_from_sqs():
    # To be run by a human to review entries on an SQS queue.
    while True:
        response = sqs.receive_message(QueueUrl=DLQ_URL)
        if not response.get("Messages"):
            logger.info("No more films to process.")
            break
        for msg in response["Messages"]:
            yield json.loads(msg["Body"])
            sqs.delete_message(QueueUrl=DLQ_URL, ReceiptHandle=msg["ReceiptHandle"])


def prompt_best_match(results) -> str | None:
    choices_hints = {}
    for result in results:
        try:
            imdb_id = result["movie"]["ids"]["imdb"]
        except KeyError:
            # If there's no imdb then it's probably a low quality entry.
            continue
        year = result["movie"].get("year", "Unknown")
        title = result["movie"]["title"]
        score = int(result["score"])
        choice = (f"{title} ({year}) [score: {score}]", imdb_id)
        hint = f"https://www.imdb.com/title/{imdb_id}/"
        choices_hints[choice] = hint

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

    # Move this boilerplate somewhere? Global?
    secrets = get_secret("TraktAPI")
    trakt = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])

    user_id = secrets["USER_ID"]
    list_id = secrets["LIST_ID"]
    api_list = trakt.list(user_id, list_id)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    process_parser = subparsers.add_parser(
        "process", help="Manually review the films in an AWS queue."
    )
    process_parser.add_argument("--aws_queue", default=DLQ_URL)
    add_parser = subparsers.add_parser("add")
    group = add_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--title")
    group.add_argument("--imdb_id")

    args = parser.parse_args()

    # There's a tidier way to do all this. We want to figure out a list
    # of films to add. That list either comes from SQS (after review) or
    # from the command line (a list of one) So build that list (of imdb
    # ids) and then add them all at the end.
    if args.command == "process":
        for article_data in get_articles_from_sqs():
            article = Article(article_data["webTitle"], article_data["webUrl"])
            print(article.web_title)
            print(article.web_url)
            # TODO: Prompt for confirmation to add this film?
            results = trakt.search.by_text(article.film_title)
            imdb_id = prompt_best_match(results)
            if imdb_id:
                api_list.add([imdb_id])

    elif args.command == "add":
        if args.imdb_id:
            print(f"Select best match for imdb_id '{args.imdb_id}'")
            results = trakt.search.by_id(args.imdb_id)
        else:
            print(f'Select best match for "{args.title}"')
            results = trakt.search.by_text(args.title)
        imdb_id = prompt_best_match(results)
        if imdb_id:
            api_list.add([imdb_id])
