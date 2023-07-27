import json
import sys
import time
from datetime import datetime, timedelta

import requests

from aws_utils import get_secret, put_secret

# A script to mimic the "device" authentication flow. The device is actually
# the lambda functions that will make API calls and rotate the secrets.
# Consider using Parameter Store and rotating/refreshing secrets on API
# call (ie every night)
BASE_URL = "https://api.trakt.tv"
DEVICE_CODE_URL = BASE_URL + "/oauth/device/code"
GET_TOKEN_URL = BASE_URL + "/oauth/device/token"

headers = {"Content-Type": "application/json"}
secrets = get_secret("TraktAPI")
data = {"client_id": secrets["CLIENT_ID"]}
requests.post("https://api.trakt.tv/oauth/device/code")
response = requests.post(DEVICE_CODE_URL, data=json.dumps(data), headers=headers)
if response.status_code != 200:
    raise Exception(response.status_code)

body = response.json()
verification_url = body["verification_url"]
user_code = body["user_code"]
device_code = body["device_code"]
interval = body["interval"]
expires_in = datetime.now() + timedelta(seconds=int(body["expires_in"]))

print(f'Please visit {verification_url} and enter the code "{user_code}".')

data = {
    "code": device_code,
    "client_id": secrets["CLIENT_ID"],
    "client_secret": secrets["CLIENT_SECRET"],
}
access_token = None
refresh_token = None
sys.stdout.write("\n")
while datetime.now() < expires_in:
    time.sleep(interval)
    response = requests.post(GET_TOKEN_URL, data=json.dumps(data), headers=headers)
    if response.status_code == 200:
        body = response.json()
        access_token = body["access_token"]
        refresh_token = body["refresh_token"]
        sys.stdout.write("✓")
        break
    else:
        sys.stdout.write(".")
    sys.stdout.flush()
if not access_token or not refresh_token:
    print("Code was not entered in time. Please retry again.")
    sys.exit(1)

secrets["ACCESS_TOKEN"] = access_token
secrets["REFRESH_TOKEN"] = refresh_token

put_secret("TraktAPI", secrets)
