import json
from functools import cache

import boto3


@cache
def get_secret(secret_id):
    """
    Helper function to get the contents of a given secret.
    """
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name="eu-west-2")
    response = client.get_secret_value(SecretId=secret_id)
    return json.loads(response["SecretString"])


def put_secret(secret_id, secret_values):
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name="eu-west-2")
    return client.update_secret(
        SecretId=secret_id,
        SecretString=json.dumps(secret_values),
    )
