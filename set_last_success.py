import sys
from datetime import datetime

import boto3

DATE_FORMAT = r"%Y-%m-%d"

# A helper script to manually set the Last Success parameter
# from the command line. Useful for active debugging.

if len(sys.argv) == 2:
    # Validate by converting to datetime
    dt = datetime.strptime(sys.argv[1], DATE_FORMAT)
else:
    dt = datetime.now()

session = boto3.Session()
client = session.client(service_name="ssm", region_name="eu-west-2")
client.put_parameter(
    Name="GoodFilms/LastSuccess",
    Value=dt.strftime(DATE_FORMAT),
    Type="String",
    Overwrite=True,
)
print(f"GoodFilms/LastSuccess set to {dt.strftime(DATE_FORMAT)}")
