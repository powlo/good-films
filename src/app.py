import guardian_api
import trakt_api


def lambda_handler(event, context):
    films = guardian_api.get_films()
    trakt_api.post_films(films)
