from unittest import TestCase, mock

from mock_functions import mock_get, mock_get_secret_value

from trakt_api import update_list


class TestPostFilmIds(TestCase):
    @mock.patch("requests.get", mock_get)
    @mock.patch("requests.post")
    @mock.patch("boto3.Session")
    def test_simple(self, mock_session, mock_post):
        mock_session.return_value.client.return_value.get_secret_value = (
            mock_get_secret_value
        )
        update_list({"tt123"})
        self.assertTrue(mock_post.called)
        mock_post.assert_called_once_with(
            "https://api.trakt.tv/users/ukdefresit/lists/guardian-films/items",
            data='{"movies": [{"ids": {"imdb": "tt123"}}]}',
            headers={
                "Content-Type": "application/json",
                "trakt-api-version": "2",
                "Authorization": "Bearer 123abc",
                "trakt-api-key": "bac123",
            },
        )
