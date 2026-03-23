import logging
import os
from dataclasses import asdict, dataclass

import boto3
import trakt_api
from aws_utils import get_secret

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


UNPROCESSABLE_QUEUE_URL = os.environ["UNPROCESSABLE_QUEUE_URL"]


@dataclass
class Article:
    web_title: str
    web_url: str
    references: list


def get_title(article: Article) -> str:
    seperator = " review \u2013 "  # u2013 is an n-dash
    return article.web_title.split(seperator)[0]


def get_imdb_id(article: Article):
    for ref in article.references:
        if ref["type"] == "imdb":
            id = ref["id"].split("/")[-1]
            return id


def lambda_handler(event, context):
    # Better to define client outside?
    sqs = boto3.client("sqs")

    for message in event["Records"]:
        secrets = get_secret("TraktAPI")
        user_id = secrets["USER_ID"]
        list_id = secrets["LIST_ID"]
        api = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])

        body = message["body"]
        try:
            article = Article(
                web_title=body["webTitle"],
                web_url=body["webUrl"],
                references=body["references"],
            )
        except Exception as e:
            # If we can't form a proper article, then probably best to ignore.
            logger.error(e)
            continue
        imdb_id = get_imdb_id(article)

        if not imdb_id:
            logger.warning(
                f'No imdb id for for "{article.web_title}" ({article.web_url})'
            )
            sqs.send_message(
                QueueUrl=UNPROCESSABLE_QUEUE_URL, MessageBody=asdict(article)
            )
            continue
        trakt_list = api.list(user_id, list_id)
        trakt_list.add([imdb_id])
        title = get_title(article)
        logger.info(f'Added "{title}" to trakt list.')


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
