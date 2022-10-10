import json
import logging
import requests
from pprint import pprint as P

DEBUGGING = False
headers = {'content-type': 'application/json'}

def log(txt):
    if not DEBUGGING:
        return
    P(txt)

with open("input_voyages.txt", "r") as f:
    URL = f.read()

response = requests.post(URL, headers = headers)
try:
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    P(e)
P("****************")
P(response)
P("****************")
with open("output_voyages.json", "w") as f:
    f.write(json.dumps(response.json()))


