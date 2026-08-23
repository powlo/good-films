import json
import logging
from dataclasses import dataclass

import boto3
import trakt_api
from aws_utils import get_secret

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class Reference:
    type: str
    id: str


@dataclass
class Article:
    web_title: str
    web_url: str
    references: list[Reference]

    def __post_init__(self):
        if not isinstance(self.references, list):
            raise TypeError("items must be a list.")

        if len(self.references) == 0:
            raise ValueError("items must be a non-empty list.")

        if not any([r.type == "imdb" for r in self.references]):
            raise ValueError("No imdb references found.")

    @property
    def title(self) -> str:
        seperator = " review \u2013 "  # u2013 is an n-dash
        return self.web_title.split(seperator)[0]

    @property
    def imdb_id(self):
        imdb_references = [r for r in self.references if r.type == "imdb"]
        first = imdb_references[0]
        return first.id.split("/")[-1]


def lambda_handler(event, context):
    for message in event["Records"]:
        secrets = get_secret("/GoodFilms/TraktAPI")
        user_id = secrets["USER_ID"]
        list_id = secrets["LIST_ID"]
        api = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])

        body = json.loads(message["body"])
        article = Article(
            web_title=body["webTitle"],
            web_url=body["webUrl"],
            references=body["references"],
        )
        trakt_list = api.list(user_id, list_id)
        trakt_list.add([article.imdb_id])
        logger.info(f'Added "{article.title}" to trakt list.')


def excess_hander():
    # Code stashed away. We will need to trim the list at some point.
    # This is how we did it before.
    excess = max(len(list_items) + len(imdb_ids) - max_list_size, 0)
    if excess:
        logger.warning(
            "Too many items in the list. List will be truncated to make room."
        )
        items_to_delete = list_items[:excess]
        imdb_ids_to_delete = [item["movie"]["ids"]["imdb"] for item in items_to_delete]
        response = api_list.delete(imdb_ids_to_delete)
        logger.info("Deleted %s from list." % response["deleted"]["movies"])
        logger.info("List now contains %s items." % response["list"]["item_count"])
