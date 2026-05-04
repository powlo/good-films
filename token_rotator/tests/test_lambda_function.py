import json

from lambda_function import lambda_handler


def test_create_secret(mocker):
    mock_client = mocker.patch("lambda_function.client")
    mock_client.describe_secret.return_value = {
        "RotationEnabled": True,
        "VersionIdsToStages": {"token123": "AWSPENDING"},
    }
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "REFRESH_TOKEN": "refresh123",
                "CLIENT_ID": "clientid123",
                "CLIENT_SECRET": "clientsecret123",
            }
        )
    }

    mock_http = mocker.patch("lambda_function.http")
    mock_http.request.return_value.status = 200
    mock_http.request.return_value.data = json.dumps(
        {"access_token": "accesstoken123", "refresh_token": "refreshtoken123"}
    )

    event = {"SecretId": 3, "ClientRequestToken": "token123", "Step": "createSecret"}
    lambda_handler(event, None)
    assert mock_http.request.called
    assert mock_client.put_secret_value.called
