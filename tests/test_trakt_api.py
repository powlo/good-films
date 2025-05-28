import json
from unittest import TestCase, mock

from mock_functions import mock_get

from trakt_api import TraktAPI, update_list

mock_secret = mock.MagicMock(
    return_value={
        "ACCESS_TOKEN": "123abc",
        "CLIENT_ID": "bac123",
        "USER_ID": "auser",
        "LIST_ID": "alist",
        "MAX_LIST_SIZE": "5",
    }
)


# Testing the high level function that corral concierge collate like a museum.
class TestUpdateList(TestCase):
    @mock.patch("boto3.Session", mock.MagicMock)
    @mock.patch("trakt_api.requests.Session")
    @mock.patch("trakt_api.get_secret", mock_secret)
    def test_simple(self, mock_session):
        mock_session.return_value.get = mock.MagicMock(side_effect=mock_get)

        update_list({"tt123"})
        mock_post = mock_session.return_value.post
        self.assertTrue(mock_post.called)
        mock_post.assert_called_once_with(
            "https://api.trakt.tv/users/auser/lists/alist/items",
            data='{"movies": [{"ids": {"imdb": "tt123"}}]}',
        )


# Testing the "routes" that we've put in trakt_api.py
# These are really only testing that we've built the url correctly.
# Could split out into just instantiating the route classes.
class TestSearch(TestCase):
    @mock.patch("trakt_api.requests.Session")
    def test_simple(self, mock_session):

        api = TraktAPI("fake_clientid", "fake_accesstoken")
        api.search.by_id("tt123")
        mock_get = mock_session.return_value.get
        self.assertTrue(mock_get.called)
        mock_get.assert_called_once_with(
            "https://api.trakt.tv/search/imdb/tt123?type=movie"
        )


@mock.patch("trakt_api.requests.Session")
class TestList(TestCase):
    def test_get(self, mock_session):

        api = TraktAPI("fake_clientid", "fake_accesstoken")
        api.list("fake_user_id", "fake_list_id").get()
        mock_get = mock_session.return_value.get
        self.assertTrue(mock_get.called)
        mock_get.assert_called_once_with(
            "https://api.trakt.tv/users/fake_user_id/lists/fake_list_id/items/movies/added/desc"
        )

    def test_add(self, mock_session):
        api = TraktAPI("fake_clientid", "fake_accesstoken")
        imdb_ids = set(["tt123", "tt456"])
        api.list("auser", "alist").add(imdb_ids)
        mock_post = mock_session.return_value.post
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args.args
        self.assertEqual(
            "https://api.trakt.tv/users/auser/lists/alist/items", call_args[0]
        )
        call_kwargs = mock_post.call_args.kwargs
        self.assertTrue("data" in call_kwargs)
        data_kwarg = json.loads(call_kwargs["data"])
        self.assertTrue({"ids": {"imdb": "tt123"}} in data_kwarg["movies"])
        self.assertTrue({"ids": {"imdb": "tt123"}} in data_kwarg["movies"])

    def test_delete(self, mock_session):
        api = TraktAPI("fake_clientid", "fake_accesstoken")
        imdb_ids = set(["tt123", "tt456"])
        api.list("auser", "alist").delete(imdb_ids)
        mock_post = mock_session.return_value.post
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args.args
        self.assertEqual(
            "https://api.trakt.tv/users/auser/lists/alist/items/remove", call_args[0]
        )

        call_kwargs = mock_post.call_args.kwargs

        self.assertTrue("data" in call_kwargs)
        data_kwarg = json.loads(call_kwargs["data"])
        self.assertTrue({"ids": {"imdb": "tt123"}} in data_kwarg["movies"])
        self.assertTrue({"ids": {"imdb": "tt123"}} in data_kwarg["movies"])
