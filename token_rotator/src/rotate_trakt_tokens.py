import json
import logging

import boto3
import urllib3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client("secretsmanager")
http = urllib3.PoolManager()


def lambda_handler(event, context):
    arn = event["SecretId"]  # this is the secret we're changing.
    token = event["ClientRequestToken"]  # this is the new versionId.
    step = event["Step"]  # The step that we're going to perform.

    # Boilerplate copied from AWS:
    metadata = client.describe_secret(SecretId=arn)
    if not metadata["RotationEnabled"]:
        logger.error("Secret %s is not enabled for rotation" % arn)
        raise ValueError("Secret %s is not enabled for rotation" % arn)
    versions = metadata["VersionIdsToStages"]
    if token not in versions:
        logger.error(
            "Secret version %s has no stage for rotation of secret %s." % (token, arn)
        )
        raise ValueError(
            "Secret version %s has no stage for rotation of secret %s." % (token, arn)
        )
    if "AWSCURRENT" in versions[token]:
        logger.info(
            "Secret version %s already set as AWSCURRENT for secret %s." % (token, arn)
        )
        return
    elif "AWSPENDING" not in versions[token]:
        logger.error(
            "Secret version %s not set as AWSPENDING for rotation of secret %s."
            % (token, arn)
        )
        raise ValueError(
            "Secret version %s not set as AWSPENDING for rotation of secret %s."
            % (token, arn)
        )

    if step == "createSecret":
        logger.info("createSecret. Start (ARN: %s, token %s)" % (arn, token))

        secrets = json.loads(
            client.get_secret_value(SecretId=arn, VersionStage="AWSCURRENT")[
                "SecretString"
            ]
        )

        data = {
            "refresh_token": secrets["REFRESH_TOKEN"],
            "client_id": secrets["CLIENT_ID"],
            "client_secret": secrets["CLIENT_SECRET"],
            "redirect_uri": "",
            "grant_type": "refresh_token",
        }

        headers = {"Content-Type": "application/json"}

        response = http.request(
            "POST",
            "https://api.trakt.tv/oauth/token",
            body=json.dumps(data),
            headers=headers,
        )
        if response.status != 200:
            # TODO: If the access token is now invalid, we should
            # re-initilise completely. Ie make call to create_trakt_tokens.
            error_json = json.loads(response.data)
            error_message = (
                str(response.status)
                + " "
                + response.reason
                + ". "
                + error_json["error_description"]
            )
            raise ValueError(error_message)
        new_tokens = json.loads(response.data)
        secrets["ACCESS_TOKEN"] = new_tokens["access_token"]
        secrets["REFRESH_TOKEN"] = new_tokens["refresh_token"]
        client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=json.dumps(secrets),
            VersionStages=["AWSPENDING"],
        )
        logger.info("createSecret: Success.")

    elif step == "setSecret":
        logger.info("setSecret: Nothing to do here.")

    elif step == "testSecret":
        logger.info("testSecret. Start (ARN: %s, token %s)" % (arn, token))

        secrets = json.loads(
            client.get_secret_value(
                SecretId=arn, VersionId=token, VersionStage="AWSPENDING"
            )["SecretString"]
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer %s" % secrets["ACCESS_TOKEN"],
            "trakt-api-version": "2",
            "trakt-api-key": "%s" % secrets["CLIENT_ID"],
        }
        response = http.request(
            "GET",
            "https://api.trakt.tv/users/ukdefresit/lists/guardian-films",
            headers=headers,
        )
        if response.status == 200:
            logger.info("testSecret: Success.")
        else:
            logger.error(
                "testSecret: Unable to authorize with the pending "
                "secret of secret ARN %s" % arn
            )
            raise ValueError(
                "Unable to connect to Trakt with pending secret of secret ARN %s" % arn
            )

    elif step == "finishSecret":
        logger.info("finishSecret. Start (ARN: %s, token %s)" % (arn, token))

        metadata = client.describe_secret(SecretId=arn)
        current_version = None
        for version_id, stages in metadata["VersionIdsToStages"].items():
            if "AWSCURRENT" in stages:
                current_version = version_id
                break

        client.update_secret_version_stage(
            SecretId=arn,
            VersionStage="AWSCURRENT",
            MoveToVersionId=token,
            RemoveFromVersionId=current_version,
        )
        logger.info("finishSecret. Success.")

    else:
        logger.warn('Unrecognised step: "%s"' % step)
