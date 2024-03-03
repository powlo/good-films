from datetime import datetime
from unittest import TestCase, mock

from mock_functions import mock_get

import app


class TestLambdaHandler(TestCase):

    @mock.patch("guardian_api.get_secret", lambda _: {"API_KEY": "123"})
    @mock.patch(
        "trakt_api.get_secret", lambda _: {"ACCESS_TOKEN": "123", "CLIENT_ID": "abc123"}
    )
    @mock.patch("app.get_parameter", lambda _: "2024-2-29")
    @mock.patch("app.put_parameter", mock.MagicMock)
    @mock.patch("requests.get", mock.MagicMock(side_effect=mock_get))
    @mock.patch("requests.post")
    def test_film_posted_to_trakt(self, mock_post):
        app.lambda_handler(None, None)
        self.assertTrue(mock_post.called)
        mock_post.assert_called_once_with(
            "https://api.trakt.tv/users/ukdefresit/lists/guardian-films/items",
            data='{"movies": [{"ids": {"trakt": 7}}]}',
            headers={
                "Content-Type": "application/json",
                "trakt-api-version": "2",
                "Authorization": "Bearer 123",
                "trakt-api-key": "abc123",
            },
        )

    @mock.patch("app.trakt_api.post_film_ids", mock.MagicMock)
    @mock.patch("app.guardian_api.get_films", mock.MagicMock(return_value=[]))
    @mock.patch("app.get_parameter", lambda _: "2024-2-29")
    @mock.patch("app.datetime")
    @mock.patch("app.put_parameter")
    def test_parameter_updated(self, mock_put_parameter, mock_datetime):
        mock_datetime.now.return_value = datetime(2024, 3, 2)
        app.lambda_handler(None, None)
        self.assertTrue(mock_put_parameter.called)
        mock_put_parameter.assert_called_once_with(
            "GoodFilms_LastSuccess", "2024-03-02"
        )
