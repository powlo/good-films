# Good-Films

![Build Status](https://codebuild.eu-west-2.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoiUkhvVzRLa0VXeWJIMlJKNW0rVUxhMFdJSmNGYkU1b3VKUEtES2RwMm45dVJmZDQydUJjR2ptSkZ1RmdGMmllNzhmcGFMVGtEMVhPV2dCWDRiaHFwcWFrPSIsIml2UGFyYW1ldGVyU3BlYyI6Ik1INWFQYThnYVh5OGlNK1IiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master)

An AWS Serverless Application that scrapes the guardian api and posts film reviews to trakt.

Documentation for Guardian API is found here: https://open-platform.theguardian.com/documentation/

Documentation for Trakt API is found here: https://trakt.docs.apiary.io/

## Trakt Tokens.

Access and refresh tokens for Trakt need to be rotated. These tokens are stored in AWS Secrets Manager and are rotated automatically through the `TraktTokenRotator` lambda function.

In the event that the refresh token is stale the tokens will have to be manually regenerated.

To do this run `python create_trakt_tokens.py` and follow on screen instructions.