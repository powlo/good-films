# TMDB experimentation

import os

import requests

TMDB_API_KEY = os.environ["TMDB_API_KEY"]
TMDB_ACCESS_TOKEN = os.environ["TMDB_ACCESS_TOKEN"]
TMDB_BASE_URL = "https://api.themoviedb.org/3/"
TMDB_LIST_ID = 8688343
TMDB_ACCOUNT_ID = os.environ["TMDB_ACCOUNT_ID"]
TMDB_LIST_ID = os.environ["TMDB_LIST_ID"]
TMDB_USERNAME = os.environ["TMDB_USERNAME"]
TMDB_PASSWORD = os.environ["TMDB_PASSWORD"]

# Must use some form of authentication. Otherwise 401.
# Either:
requests.get(f"https://api.themoviedb.org/3/movie/550?api_key={TMDB_API_KEY}")
# or:
headers = {
    "Authorization": f"Bearer {TMDB_ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "accept": "application/json",
}
requests.get(f"{TMDB_BASE_URL}movie/550", headers=headers)
results = requests.get(
    f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query=the+avengers"
)

# use the access token to generate a request token:
# (Can also use the API_KEY as a get parameter)
url = TMDB_BASE_URL + "authentication/token/new"
response = requests.get(url, headers=headers)
request_token = response.json()["request_token"]

# Either
# 1) Direct the user (assumed to be logged in) to interactively approve the app / authenticate.
url = f"https://www.themoviedb.org/authenticate/{request_token}"

# Or
# 2) "Validate" the request token by associating a username and password.
url = TMDB_BASE_URL + "authentication/token/validate_with_login"
data = {
    "username": TMDB_USERNAME,
    "password": TMDB_PASSWORD,
    "request_token": request_token,
}
response = requests.post(url, headers=headers, json=data)

# Now create a session id with the "validated" request token.
url = TMDB_BASE_URL + "authentication/session/new"
data = {"request_token": request_token}
response = requests.post(url, headers=headers, json=data)
session_id = response.json()["session_id"]

# Get account info:
f"https://api.themoviedb.org/3/account"
requests.get(url, headers=headers).json()

# Get the users lists:
url = f"https://api.themoviedb.org/3/account/{TMDB_ACCOUNT_ID}/lists"

# Post to the list
url = f"https://api.themoviedb.org/3/list/{TMDB_LIST_ID}/add_item"
params = {"session_id": session_id}
data = {"media_id": 1492865}
response = requests.post(url, headers=headers, params=params, json=data)
