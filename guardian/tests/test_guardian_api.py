import unittest
from datetime import datetime
from unittest import mock

import app


@mock.patch("app.get_secret", lambda _: {"API_KEY": "123"})
@mock.patch("app.requests.get")
class TestGuardianAPI(unittest.TestCase):
    def test_get_articles(self, mock_get):
        article_data = {
            "webTitle": "a film review",
            "webUrl": "www.aurl.com",
            "references": [{"type": "imdb", "id": "imdb/tt123456"}],
        }
        mock_get.return_value.json.return_value = {
            "response": {
                "results": [article_data],
                "pages": 1,
            }
        }
        yesterday = datetime(2024, 2, 29)
        articles = list(app.get_articles(yesterday))
        self.assertEqual(1, len(list(articles)))
        article = articles[0]

        # TODO: Switch to dataclass and do x in y.
        self.assertEqual(article, article_data)
