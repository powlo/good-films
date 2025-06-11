import logging
import os
import sys
from datetime import datetime

import inquirer

import guardian_api
import trakt_api
from aws_utils import get_parameter, get_secret, put_parameter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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

    # TODO: Instead of prompting, add these films to an SQS Queue.
    films_no_id = [f for f in films if not f["imdb_id"]]
    for f in films_no_id:
        logger.warning(f'No imdb id found for "{f["title"]}"')
        # The env var being set indicates that we're running in an AWS Lambda.
        if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            imdb_id = prompt_best_match(f["title"], f["url"])
            imdb_ids.append(imdb_id)

    trakt_api.update_list(imdb_ids)

    # Update the "LastSuccess" parameter ready for the next run.
    now = datetime.now()
    put_parameter("GoodFilms_LastSuccess", now.strftime("%Y-%m-%d"))


def manual_add():
    # Manually run this to add films that don't have any references.
    # Todo: Allow the lambda handler above to dump to a queue and
    # then we run the manual handler over that queue.
    last_success = get_parameter("GoodFilms_LastSuccess")
    from_date = input(f"From Date ({last_success}): ")
    if not from_date:
        from_date = last_success
    from_date = datetime.strptime(from_date, "%Y-%m-%d")

    films = []
    for article in guardian_api.get_articles(from_date):
        film = guardian_api.parse(article)
        films.append(film)

    films = [f for f in films if not f["imdb_id"]]
    logger.info(f"Found {len(films)} films with no imdb id.")

    secrets = get_secret("TraktAPI")
    trakt = trakt_api.TraktAPI(secrets["CLIENT_ID"], secrets["ACCESS_TOKEN"])
    for film in films:
        imdb_id = prompt_best_match(film["title"], film["url"])
        if imdb_id:
            user_id = secrets["USER_ID"]
            list_id = secrets["LIST_ID"]
            api_list = trakt.list(user_id, list_id)
            api_list.add([imdb_id])


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
        year = result["movie"]["year"] or "Unknown Year"
        title = result["movie"]["title"]
        score = int(result["score"])
        imdb_id = result["movie"]["ids"]["imdb"]
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
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    lambda_handler(None, None)
