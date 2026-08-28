import json
import logging
import os
from dataclasses import dataclass

import spacy
from aws_utils import get_secret

from .tmdb_api import TmdbAPI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TMDB_READ_ACCESS_TOKEN = os.environ["TMDB_READ_ACCESS_TOKEN"]
TMDB_USERNAME = os.environ["TMDB_USERNAME"]
TMDB_PASSWORD = os.environ["TMDB_PASSWORD"]
TMDB_LIST_ID = int(os.environ["TMDB_LIST_ID"])


@dataclass
class Reference:
    type: str
    id: str


@dataclass
class Article:
    web_title: str
    web_url: str
    body_text: str

    @property
    def film_title(self) -> str:
        seperator = " review \u2013 "  # u2013 is an n-dash
        return self.web_title.split(seperator)[0]


# ur here
# Now: backfill the queue with films.
# Run the tmdb service locally and see what happens.


def lambda_handler(event, context):
    for message in event["Records"]:
        secrets = get_secret("/GoodFilms/TraktAPI")
        user_id = secrets["USER_ID"]
        list_id = secrets["LIST_ID"]
        tmdb_api = TmdbAPI(
            read_access_token=TMDB_READ_ACCESS_TOKEN,
            username=TMDB_USERNAME,
            password=TMDB_PASSWORD,
        )

        article_data = json.loads(message["body"])
        article = Article(
            article_data["webTitle"],
            article_data["webUrl"],
            article_data["fields"]["bodyText"],
        )
        # Get all the matching films from TMDB
        # TODO: break this out.
        logger.info(f'Searching TMDB for "{article.film_title}".')

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

        if tmdb_films:
            best_match = tmdb_films[0]

            logger.info(
                f'Best match: "{best_match['title']} ({best_match['release_date']} [score: {best_match['score']}])"'
            )
            tmdb_api.add(
                int(best_match["id"]),
                TMDB_LIST_ID,
            )
            logger.info(f'Added "{best_match['title']}" to trakt list.')


def similarity(text1, text2):
    nlp = spacy.load("en_core_web_md")
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    return doc1.similarity(doc2)
