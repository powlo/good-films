import json
from unittest import mock


def mock_get(*args, **kwargs):
    """
    Returns a response based on the URL that's passed in.
    """
    # When testing the app, mocking requests.get is tricky because
    # multiple calls to the function are made during a single call
    # to the lambda_handler in app.py.
    # We can't just patch twice, we have to do this url inspection
    # to determine the right response to return in each case.
    url = args[0]
    if "guardian" in url:
        mock_film = {
            "webTitle": "a film review",
            "webUrl": "www.aurl.com",
            "references": [{"type": "imdb", "id": "imdb/tt123456"}],
        }
        data = {
            "response": {
                "results": [mock_film],
                "pages": 1,
            }
        }
    elif "trakt" in url:
        data = [
            {
                "type": "movie",
                "score": 1000,
                "movie": {
                    "title": "A Film",
                    "year": 1987,
                    "ids": {
                        "trakt": 7,
                        "slug": "a-film-1987",
                        "imdb": "tt123456",
                        "tmdb": 12,
                    },
                },
            }
        ]
    else:
        raise AttributeError("Unknown URL. Cannot generate mock response.")
    mock_response = mock.MagicMock()
    mock_response.json.return_value = data
    return mock_response


def mock_get_secret_value(*args, **kwargs):
    """
    Mocks AWS get_secret_value
    """
    return {
        "SecretString": json.dumps(
            {
                "ACCESS_TOKEN": "123abc",
                "CLIENT_ID": "bac123",
            }
        )
    }
