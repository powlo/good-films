import unittest
from unittest import mock

import guardian_api


@mock.patch("guardian_api.get_secret", lambda _: {"API_KEY": "123"})
@mock.patch("guardian_api.requests.get")
class TestGuardianAPI(unittest.TestCase):
    def test_get_films(self, mock_get):
        mock_film = {
            "webTitle": "a film review",
            "webUrl": "www.aurl.com",
            "references": [{"type": "imdb", "id": "imdb/tt123456"}],
        }
        mock_get.return_value.json.return_value = {
            "response": {
                "results": [mock_film],
                "pages": 1,
            }
        }
        films = next(guardian_api.get_films())
        self.assertEqual(1, len(list(films)))
        self.assertTrue(mock_film in films)

    def test_extract_imdb_ids(self, mock_get):
        results = [
            {
                "webTitle": "a film review",
                "webUrl": "www.aurl.com",
                "references": [{"type": "imdb", "id": "imdb/tt123456"}],
            }
        ]
        films = guardian_api.extract_imdb_ids(results)
        self.assertTrue("tt123456" in films)
