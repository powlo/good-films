#!/usr/bin/env python
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
import spacy
from tmdb_api import TmdbAPI

DLQ_URL = os.environ["DLQ_URL"]
TMDB_API_KEY = os.environ["TMDB_API_KEY"]
TMDB_READ_ACCESS_TOKEN = os.environ["TMDB_READ_ACCESS_TOKEN"]
TMDB_USERNAME = os.environ["TMDB_USERNAME"]
TMDB_PASSWORD = os.environ["TMDB_PASSWORD"]
TMDB_LIST_ID = int(os.environ["TMDB_LIST_ID"])

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__file__)
sqs = boto3.client("sqs")


@dataclass
class Article:
    web_title: str
    web_url: str
    body_text: str

    @property
    def film_title(self) -> str:
        seperator = " review \u2013 "  # u2013 is an n-dash
        return self.web_title.split(seperator)[0]


def similarity(text1, text2):
    nlp = spacy.load("en_core_web_md")
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    return doc1.similarity(doc2)


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

    default_choice = results[0]["title"]
    for result in results:
        tmdb_id = result["id"]
        release_date = result["release_date"]
        title = result["title"]
        score = "%.2f" % result["score"]
        choice = (f"{title} ({release_date}) [score: {score}]", tmdb_id)
        hint = f"https://www.themoviedb.org/movie/{tmdb_id}/"
        choices_hints[choice] = hint

    choices_hints[("[ Skip ]", None)] = None
    questions = [
        inquirer.List(
            "tmdb_id",
            message="Select matching film:",
            choices=choices_hints.keys(),
            hints=choices_hints,
            default=default_choice,
        ),
    ]
    answer = inquirer.prompt(questions)
    if answer:
        return answer["tmdb_id"]


if __name__ == "__main__":

    tmdb_api = TmdbAPI(
        read_access_token=TMDB_READ_ACCESS_TOKEN,
        username=TMDB_USERNAME,
        password=TMDB_PASSWORD,
    )

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    process_parser = subparsers.add_parser(
        "process", help="Manually review the films in an AWS queue."
    )
    process_parser.add_argument("--aws_queue", default=DLQ_URL)
    add_parser = subparsers.add_parser("add")
    group = add_parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--title")
    group.add_argument("--tmdb_id")

    args = parser.parse_args()

    # There's a tidier way to do all this. We want to figure out a list
    # of films to add. That list either comes from SQS (after review) or
    # from the command line (a list of one) So build that list (of tmdb
    # ids) and then add them all at the end.
    if args.command == "process":
        for article_data in get_articles_from_sqs():
            article = Article(
                article_data["webTitle"],
                article_data["webUrl"],
                article_data["fields"]["bodyText"],
            )
            logger.debug(f'Article Title: "{article.web_title}"')
            logger.debug(f'Article URL: "{article.web_url}"')

            # Get all the matching films from TMDB
            # We can be smart and return an iterable object.
            response = tmdb_api.search(article.film_title)
            page = response["page"]
            total_pages = response["total_pages"]
            tmdb_films = [
                x for x in response["results"] if x["title"] == article.film_title
            ]
            for page in range(1, total_pages):
                response = tmdb_api.search(article.film_title, page)
                page = response["page"]
                total_pages = response["total_pages"]
                filtered_results = [
                    x for x in response["results"] if x["title"] == article.film_title
                ]
                tmdb_films.extend(filtered_results)

            for film in tmdb_films:
                # Rank results by similarity to article
                film["score"] = similarity(article.body_text, film["overview"])

            tmdb_films.sort(key=lambda x: x["score"])

            # if interactive then prompt?
            tmdb_id = prompt_best_match(tmdb_films)
            if tmdb_id:
                tmdb_api.add(
                    int(tmdb_id),
                    TMDB_LIST_ID,
                )

    elif args.command == "add":
        response = tmdb_api.search(args.title)
        if not response["results"]:
            print(f"No matching results for '{args.title}' found.")
            sys.exit(0)
        for result in response["results"]:
            result["score"] = similarity(args.title, result["title"])
        response["results"].sort(key=lambda x: x["score"], reverse=True)
        print(f'Select best match for "{args.title}"')
        tmdb_id = prompt_best_match(response["results"])
        if tmdb_id:
            tmdb_api.add(int(tmdb_id), TMDB_LIST_ID)
