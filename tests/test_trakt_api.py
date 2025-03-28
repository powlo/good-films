from unittest import TestCase, mock

import requests
from mock_functions import mock_get

from trakt_api import update_list


class TestUpdateList(TestCase):
    @mock.patch("boto3.Session", mock.MagicMock)
    @mock.patch("trakt_api.requests.Session")
    @mock.patch("trakt_api.get_secret")
    def test_simple(self, mock_get_secret, mock_session):
        mock_session.return_value.get = mock.MagicMock(side_effect=mock_get)
        mock_get_secret.return_value = {
            "ACCESS_TOKEN": "123abc",
            "CLIENT_ID": "bac123",
            "USER_ID": "auser",
            "LIST_ID": "alist",
            "MAX_LIST_SIZE": "5",
        }

        update_list({"tt123"})
        mock_post = mock_session.return_value.post
        self.assertTrue(mock_post.called)
        mock_post.assert_called_once_with(
            "https://api.trakt.tv/users/auser/lists/alist/items",
            data='{"movies": [{"ids": {"imdb": "tt123"}}]}',
        )
