import json
from datetime import datetime
from unittest import TestCase, mock

from tests.mock_functions import mock_get

with mock.patch.dict(
    "os.environ",
    {
        "GUARDIAN_ARTICLE_QUEUE_URL": "https://api.trakt.tv/users/auser/lists/alist/items"
    },
):
    import app


@mock.patch.dict("os.environ", {"AWS_LAMBDA_FUNCTION_NAME": "LambdaFunctionName"})
class TestLambdaHandler(TestCase):

    @mock.patch("app.get_secret", lambda _: {"API_KEY": "123"})
    @mock.patch("app.get_parameter", lambda _: "2024-2-29")
    @mock.patch("app.put_parameter", mock.MagicMock)
    @mock.patch("requests.get", mock.MagicMock(side_effect=mock_get))
    @mock.patch("app.sqs")
    def test_film_posted_to_sqs(self, mock_sqs):
        app.lambda_handler(None, None)
        self.assertTrue(mock_sqs.send_message.called)
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl="https://api.trakt.tv/users/auser/lists/alist/items",
            MessageBody='{"webTitle": "a film review", "webUrl": "www.aurl.com", "references": [{"type": "imdb", "id": "imdb/tt123456"}]}',
        )

    @mock.patch("app.get_articles", mock.MagicMock(return_value=[]))
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
    @mock.patch("app.put_parameter", mock.MagicMock)
    @mock.patch("app.sqs")
    @mock.patch("app.get_articles")
    def test_send_to_queue(self, mock_get_articles, mock_sqs):
        # An article with no imdb reference
        mock_article = dict(webTitle="a film", webUrl="www.aurl.com", references=None)
        mock_get_articles.return_value = [mock_article]
        app.lambda_handler(None, None)

        # The film details are sent to an SQS queue.
        mock_sqs.send_message.assert_called_once()
        message_body = mock_sqs.send_message.call_args.kwargs["MessageBody"]
        self.assertEqual(mock_article, json.loads(message_body))
