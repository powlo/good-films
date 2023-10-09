import unittest
from unittest import mock

import guardian_api


class MockAPI(object):
    def json(self):
        return {"response": {"results": [{"webTitle": "a film review"}]}}


@mock.patch("guardian_api.get_secret", lambda _: {"API_KEY": "123"})
@mock.patch("guardian_api.requests.get")
class TestGuardianAPI(unittest.TestCase):
    def test_get_films(self, mock_get):
        mock_get.return_value.json.return_value = {
            "response": {
                "results": [{"webTitle": "a film review", "webUrl": "www.aurl.com"}],
                "pages": 1,
            }
        }
        films = next(guardian_api.get_films())
        self.assertEqual(1, len(list(films)))
        self.assertEqual({"title": "a film"}, films[0])

    def test_parse_results(self, mock_get):
        results = [{"webTitle": "a film review", "webUrl": "www.aurl.com"}]
        films = guardian_api.parse_results(results)
        self.assertEqual({"title": "a film"}, films[0])
