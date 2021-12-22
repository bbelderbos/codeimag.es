import requests

base_url = "https://pybites-codeimages.herokuapp.com"
tip_create_url = f"{base_url}/create"
token_url = f"{base_url}/token"

payload = {
    "username": "pybob",
    "password": ".Nvp@K%:=?"
}
resp = requests.post(token_url, data=payload)
token = resp.json()['access_token']

headers = {"Authorization": f"Bearer {token}"}

code = """
>>> from itertools import combinations
>>> from difflib import SequenceMatcher

>>> tags = 'python pythonista developer development'.split()

>>> for pair in combinations(tags, 2):
...     similarity = SequenceMatcher(None, *pair).ratio()
...     print(pair, similarity)
...
('python', 'pythonista') 0.75
('python', 'developer') 0.13333333333333333
('python', 'development') 0.23529411764705882
('pythonista', 'developer') 0.10526315789473684
('pythonista', 'development') 0.19047619047619047
('developer', 'development') 0.8
"""
description = """🚨Another #Python Standard Library gem 🐍

So you have an API and you don't want similar items to be submitted.

Well, you can do a literal string comparison, a regex even, but ... for "almost equal" you can also use difflib's SequenceMatcher:"""
payload = {
    "title": "SequenceMatcher",
    "code": code.lstrip(),
    "description": description,
}
resp = requests.post(tip_create_url, json=payload, headers=headers)

