from datetime import datetime
from unittest import TestCase, mock

from mock_functions import mock_get

with mock.patch.dict(
    "os.environ", {"MANUAL_PROCESSING_QUEUE_URL": "https://atestqueue"}
):
    import app


@mock.patch.dict("os.environ", {"AWS_LAMBDA_FUNCTION_NAME": "LambdaFunctionName"})
class TestLambdaHandler(TestCase):

    @mock.patch("guardian_api.get_secret", lambda _: {"API_KEY": "123"})
    @mock.patch(
        "trakt_api.get_secret",
        lambda _: {
            "ACCESS_TOKEN": "123",
            "CLIENT_ID": "abc123",
            "USER_ID": "auser",
            "LIST_ID": "alist",
            "MAX_LIST_SIZE": "5",
        },
    )
    @mock.patch("app.get_parameter", lambda _: "2024-2-29")
    @mock.patch("app.put_parameter", mock.MagicMock)
    @mock.patch("requests.get", mock.MagicMock(side_effect=mock_get))
    @mock.patch("trakt_api.requests.Session")
    def test_film_posted_to_trakt(self, mock_session):
        mock_session.return_value.get = mock.MagicMock(side_effect=mock_get)
        mock_post = mock_session.return_value.post
        app.lambda_handler(None, None)
        self.assertTrue(mock_post.called)
        mock_post.assert_called_once_with(
            "https://api.trakt.tv/users/auser/lists/alist/items",
            data='{"movies": [{"ids": {"imdb": "tt123456"}}]}',
        )

    @mock.patch("app.trakt_api.update_list", mock.MagicMock)
    @mock.patch("app.guardian_api.get_articles", mock.MagicMock(return_value=[]))
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

    @mock.patch("app.get_parameter", lambda _: "2024-2-29")
    @mock.patch("app.trakt_api.update_list", mock.MagicMock)
    @mock.patch("app.put_parameter", mock.MagicMock)
    @mock.patch("app.sqs")
    @mock.patch("app.guardian_api.get_articles")
    def test_send_to_queue(self, mock_get_articles, mock_sqs):
        # An article with no imdb reference
        mock_film = {
            "webTitle": "a film review",
            "webUrl": "www.aurl.com",
            "references": [],
        }
        mock_get_articles.return_value = [mock_film]
        app.lambda_handler(None, None)

        # The film details are sent to an SQS queue.
        mock_sqs.send_message.assert_called_once()
        message_body = mock_sqs.send_message.call_args.kwargs["MessageBody"]
        self.assertTrue(mock_film, message_body)
